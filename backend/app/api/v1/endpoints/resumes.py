import json
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, get_optional_current_user, get_current_recruiter
from app.models.resume import Resume
from app.models.user import User
from app.schemas.resume import ResumeCreate, ResumeExtractRequest, ResumeOut
from app.services.pdf_extractor import extract_data_from_pdf
from app.services.nlp_normalizer import extract_address_from_text
from app.services.matching_engine import recalculate_resume_applications
from app.services.skill_cache_service import ensure_skills_cached
from app.services.vector_service import generate_embedding

router = APIRouter(prefix="/resumes", tags=["resumes"])


# 1. Extracción desde PDF (FormData para el frontend)
@router.post("/extract")
async def extract_resume_file(
    file: UploadFile = File(...), db: Session = Depends(get_db)
):
    filename = file.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo debe ser un PDF válido.",
        )

    try:
        contents = await file.read()
        extracted_data = await extract_data_from_pdf(contents, filename, db=db)
        db.commit()
        return extracted_data

    except Exception as e:
        db.rollback()
        print(f"Error procesando el PDF: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al procesar el archivo PDF: {str(e)}",
        )


# 2. Extracción desde JSON
@router.post("/extract-json")
def extract_resume_json(payload: ResumeExtractRequest):
    text = payload.raw_text.strip()
    skills = [token.strip() for token in text.split() if token.strip()][:20]
    
    # Extraer dirección desde el texto
    address = extract_address_from_text(text) or "Sin especificar"

    parsed_data = {
        "professional_title": "Perfil extraído",
        "address": address,
        "location": address,
        "summary": text[:500],
        "more_info": "",
    }
    return {
        "raw_text": text,
        "parsed_data": parsed_data,
        "extracted_skills": skills,
        "message": "Extracción mínima simulada.",
    }

# 3. Guardar/Actualizar CV
@router.post("", response_model=ResumeOut, status_code=status.HTTP_201_CREATED)
def create_resume(
    payload: ResumeCreate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    if current_user is not None and current_user.role not in ("registered", "casual"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los candidatos pueden guardar un CV.",
        )

    candidate_email = str(payload.candidate_email).strip().lower()

    # VALIDACIÓN DE SEGURIDAD:
    # Si el usuario está registrado / en sesión, el correo a guardar DEBE coincidir con el de la tabla users.
    if current_user is not None:
        user_email = str(current_user.email).strip().lower()
        if candidate_email != user_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El correo ingresado ({candidate_email}) no coincide con el correo registrado de tu cuenta activa ({user_email})."
            )

    resume = None

    if current_user is not None:
        resume = (
            db.query(Resume)
            .filter(Resume.user_id == current_user.id)
            .first()
        )

    email_resume = (
        db.query(Resume)
        .filter(func.lower(Resume.candidate_email) == candidate_email)
        .first()
    )
    if resume is None:
        resume = email_resume
    elif email_resume is not None and email_resume.id != resume.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ese correo ya está asociado a otro CV.",
        )

    if resume is not None and resume.user_id is not None:
        if current_user is None or resume.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe un CV asociado al correo leído en el análisis.",
            )

    if resume is None:
        resume = Resume()
        db.add(resume)

    resume.user_id = current_user.id if current_user is not None else None
    resume.candidate_email = candidate_email
    resume.raw_text = payload.raw_text
    resume.parsed_data = payload.parsed_data or {}
    resume.extracted_skills = payload.extracted_skills or []
    resume.file_name = payload.file_name
    if current_user is None:
        resume.expires_at = datetime.utcnow() + timedelta(days=365)
    else:
        resume.expires_at = None

    parsed_skills = payload.parsed_data.get("technical_skills", []) if payload.parsed_data else []
    soft_skills = payload.parsed_data.get("soft_skills", []) if payload.parsed_data else []
    ensure_skills_cached(db, list(parsed_skills) + list(soft_skills) + list(payload.extracted_skills or []))

    # Persist the resume data before generating and storing its work-experience vector.
    db.commit()
    db.refresh(resume)

    work_experience = (resume.parsed_data or {}).get("work_experience")
    if isinstance(work_experience, str):
        experience_text = work_experience
    elif isinstance(work_experience, list):
        experience_text = "\n".join(
            item if isinstance(item, str) else json.dumps(item, ensure_ascii=False)
            for item in work_experience
            if item
        )
    else:
        experience_text = (
            json.dumps(work_experience, ensure_ascii=False)
            if work_experience
            else ""
        )

    try:
        resume.embedding = generate_embedding(experience_text)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                f"El CV {resume.id} se guardó, pero no se pudo generar su embedding: "
                f"{exc}"
            ),
        ) from exc

    try:
        db.commit()
        db.refresh(resume)
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"El CV {resume.id} se guardó, pero no se pudo guardar su embedding."
            ),
        ) from exc

    try:
        recalculate_resume_applications(db, resume.id)
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"El CV {resume.id} se guardó, pero no se pudo recalcular el "
                "matching de sus postulaciones."
            ),
        ) from exc

    return resume

# 4. Mis CVs
@router.get("/me", response_model=list[ResumeOut])
def list_my_resumes(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    return (
        db.query(Resume)
        .filter(Resume.user_id == current_user.id)
        .order_by(Resume.created_at.desc())
        .all()
    )


# 5. Detalle por ID (Reclutadores)
@router.get("/{resume_id}", response_model=ResumeOut)
def get_resume_by_id(
    resume_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter),
):
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="CV no encontrado")
    return resume