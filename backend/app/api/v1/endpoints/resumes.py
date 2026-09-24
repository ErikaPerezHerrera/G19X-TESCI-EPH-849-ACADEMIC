from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.resume import Resume
from app.models.user import User
from app.schemas.resume import ResumeCreate, ResumeExtractRequest, ResumeOut

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post("/extract")
def extract_resume(payload: ResumeExtractRequest):
    text = payload.raw_text.strip()
    skills = [token.strip() for token in text.split() if token.strip()][:20]
    parsed_data = {
        "professional_title": "Perfil extraído",
        "location": "No especificado",
        "summary": text[:500],
    }
    return {
        "raw_text": text,
        "parsed_data": parsed_data,
        "extracted_skills": skills,
        "message": "Extracción mínima simulada: en el MVP real se sustituye por pdfplumber + NLP.",
    }


@router.post("", response_model=ResumeOut, status_code=status.HTTP_201_CREATED)
def create_resume(
    payload: ResumeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resume = Resume(
        user_id=current_user.id,
        candidate_email=payload.candidate_email,
        raw_text=payload.raw_text,
        parsed_data=payload.parsed_data or {},
        extracted_skills=payload.extracted_skills or [],
        file_name=payload.file_name,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


@router.get("/me", response_model=list[ResumeOut])
def list_my_resumes(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Resume).filter(Resume.user_id == current_user.id).order_by(Resume.created_at.desc()).all()
