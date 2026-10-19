import asyncio
import json
import logging

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
from app.services.gemini_service import (
    enrich_cv_extraction,
    enrich_cv_extraction_with_status,
)
from app.services.nlp_normalizer import extract_address_from_text
from app.services.matching_engine import recalculate_resume_applications
from app.services.skill_cache_service import ensure_skills_cached
from app.services.vector_service import generate_embedding

router = APIRouter(prefix="/resumes", tags=["resumes"])
logger = logging.getLogger(__name__)

## Ruta de Extracción de información del PDF
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
        # Espera los datos extraídos del PDF y luego intenta enriquecerlos con IA.
        extracted_data = await extract_data_from_pdf(contents, filename, db=db)
        try:
            enrichment = await asyncio.to_thread(
                enrich_cv_extraction_with_status,
                extracted_data.get("raw_text", ""),
                extracted_data,
            )
        except Exception:
            # Si la IA falla, se conserva la extracción inicial y se marca como no disponible.
            logger.exception("Falló el enriquecimiento con IA del CV; se conserva la extracción inicial.")
            enrichment = {"data": extracted_data, "ai_available": False}
        enriched_data = enrichment.get("data")
        # Si la IA devuelve datos, se actualizan los campos relevantes en la extracción final.
        if isinstance(enriched_data, dict):
            extracted_data = enriched_data
            parsed_data = extracted_data.get("parsed_data")
            if isinstance(parsed_data, dict):
                for field in (
                    "address",
                    "professional_title",
                    "technical_skills",
                    "soft_skills",
                    "work_experience",
                ):
                    if field in parsed_data:
                        extracted_data[field] = parsed_data[field]
                if isinstance(parsed_data.get("technical_skills"), list) and isinstance(
                    parsed_data.get("soft_skills"), list
                ):
                    extracted_data["extracted_skills"] = list(
                        dict.fromkeys(
                            parsed_data["technical_skills"]
                            + parsed_data["soft_skills"]
                        )
                    )
        # Se registra si la IA estuvo disponible o no para el enriquecimiento.
        ai_available = bool(enrichment.get("ai_available"))
        extracted_data["ai_enrichment_status"] = (
            "success" if ai_available else "unavailable"
        )
        db.commit()
        return extracted_data

    except Exception as e:
        db.rollback()
        logger.exception("Error procesando el PDF.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al procesar el archivo PDF."
        )


## Ruta de creación de los JSON que guardará el CV a partir de la extracción de datos del PDF y el enriquecimiento con IA
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
    enriched = enrich_cv_extraction(text, existing_data=parsed_data)
    if isinstance(enriched, dict):
        parsed_data = enriched

    return {
        "raw_text": text,
        "parsed_data": parsed_data,
        "extracted_skills": skills,
        "message": "Extracción mínima simulada.",
    }

# Ruta para guardar/actualizar CV
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
    # Si el usuario está registrado y en sesión, el correo a guardar DEBE coincidir con el de la tabla users.
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
    # Si no hay un CV relacionado al correo del candidato se crea uno nuevo
    if resume is None:
        resume = email_resume
    # Si ya existe un CV relacionado al correo del candidato y no es el mismo CV que el que se está intentando guardar, se lanza un error de conflicto
    elif email_resume is not None and email_resume.id != resume.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ese correo ya está asociado a otro CV.",
        )
    # Si ya existe un CV y el ID del usuario existe, y si el usuario actual no existe o el ID del usuario actual o ID del usuario relacionado al CV no es el mismo que el del usuario que inició la sesión lanza un error de conflicto
    if resume is not None and resume.user_id is not None:
        if current_user is None or resume.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe un CV asociado al correo leído en el análisis.",
            )

    # Si el CV no existe se ccrea uno nuevo, si existe se actualiza con los datos del payload
    if resume is None:
        resume = Resume()
        db.add(resume)

    resume.user_id = current_user.id if current_user is not None else None
    resume.candidate_email = candidate_email
    resume.raw_text = payload.raw_text
    resume.parsed_data = payload.parsed_data or {}
    resume.extracted_skills = payload.extracted_skills or []
    resume.file_name = payload.file_name
    
    # Si no hay usuario actual, se establece una fecha de expiración para el CV con 365 días a partir de la fecha actual (medida para candidato casual) Si hay un usuario actualmente registrado y que haya iniciado sesión, el CV no tiene fecha de expiración.
    if current_user is None:
        resume.expires_at = datetime.utcnow() + timedelta(days=365)
    else:
        resume.expires_at = None


    parsed_skills = payload.parsed_data.get("technical_skills", []) if payload.parsed_data else []
    soft_skills = payload.parsed_data.get("soft_skills", []) if payload.parsed_data else []
    ensure_skills_cached(db, list(parsed_skills) + list(soft_skills) + list(payload.extracted_skills or []))

    # Primero crea el CV y luego genera el embedding de la experiencia laboral.
    # Se hizo de esta forma para que si la generación del embedding falla, el CV aún se guarde y no se pierda toda la información.
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

    # Creación del emmbeding de la experiencia laboral.
    try:
        resume.embedding = generate_embedding(experience_text)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                f"El CV se guardó, pero no se pudo generar su embedding."
            ),
        ) from exc
    # Guardado del embedding de la experiencia laboral
    try:
        db.commit()
        db.refresh(resume)
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"El CV se guardó, pero no se pudo guardar su embedding."
            ),
        ) from exc
    # Recalculo del matching de las postulaciones relacionadas al CV
    try:
        recalculate_resume_applications(db, resume.id)
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"El CV se guardó, pero no se pudo recalcular el "
                "matching de sus postulaciones."
            ),
        ) from exc

    return resume

## Ruta para recuperar la información de los CVs del candidato qque inició sesión
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


# Ruta para recuperar información del un CV, solo accesible para reclutadores
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