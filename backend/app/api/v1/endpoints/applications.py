from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import (
    get_current_recruiter,
    get_current_user,
    get_optional_current_user,
)
from app.models.application import Application
from app.models.job import Job
from app.models.resume import Resume
from app.models.user import User
from app.schemas.application import ApplicationCreate, ApplicationOut, ApplicationReject
from app.services.matching_engine import recalculate_application_match
from app.services.skill_cache_service import ensure_skills_cached

router = APIRouter(prefix="", tags=["applications"])

@router.post(
    "/jobs/{job_id}/applications",
    response_model=ApplicationOut,
    status_code=status.HTTP_201_CREATED,
)
def create_application(
    job_id: UUID,
    payload: ApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    if current_user is not None and current_user.role not in ("registered", "casual"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los candidatos pueden postularse.",
        )

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Vacante no encontrada")
    if job.status != "active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esta vacante no está aceptando postulaciones.",
        )
    if job.deadline is not None:
        deadline = job.deadline
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        if deadline <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El plazo para postularse a esta vacante ha vencido.",
            )

    resume = db.query(Resume).filter(Resume.id == payload.resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="CV no encontrado")

    candidate_email = str(payload.candidate_email).lower()
    if candidate_email != resume.candidate_email.lower():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El correo de la postulación debe coincidir con el correo del CV.",
        )

    if current_user is None:
        if resume.user_id is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inicia sesión para postularte con este CV.",
            )
    elif resume.user_id is not None and resume.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El CV no pertenece al usuario autenticado.",
        )

    existing_application = (
        db.query(Application)
        .filter(
            Application.job_id == job.id,
            func.lower(Application.candidate_email) == candidate_email,
        )
        .first()
    )
    if existing_application:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una postulación para esta vacante y este correo.",
        )

    parsed_data = resume.parsed_data or {}
    raw_tech = parsed_data.get("technical_skills", [])
    raw_soft = parsed_data.get("soft_skills", [])

    ensure_skills_cached(db, list(raw_tech) + list(raw_soft))
    application = Application(
        job_id=job.id,
        user_id=current_user.id if current_user is not None else None,
        resume_id=resume.id,
        candidate_email=candidate_email,
        match_score=None,
        status="received",
        match_details={
            "raw_skills": {
                "technical_skills": raw_tech,
                "soft_skills": raw_soft,
            }
        },
    )

    db.add(application)
    db.commit()
    db.refresh(application)

    try:
        recalculate_application_match(application, db)
        db.commit()
        db.refresh(application)
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="La postulación se guardó, pero no se pudo calcular el matching.",
        ) from exc

    return application


@router.get("/applications/me", response_model=list[ApplicationOut])
def list_my_applications(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    return (
        db.query(Application)
        .options(joinedload(Application.job))  # <--- Carga eager de la relación job
        .filter(Application.user_id == current_user.id)
        .all()
    )

@router.get("/jobs/{job_id}/applications", response_model=list[ApplicationOut])
def list_job_applications(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter),
):
    return (
        db.query(Application)
        .options(joinedload(Application.resume))  # <--- Carga los datos del CV/Resume asociado
        .filter(Application.job_id == job_id)
        .order_by(Application.match_score.desc().nullslast())
        .all()
    )

# 4. Descartar postulación
@router.patch("/applications/{application_id}/reject", response_model=ApplicationOut)
def reject_application(
    application_id: UUID,
    payload: ApplicationReject,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter),
):
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Postulación no encontrada.",
        )

    application.status = "rejected"
    application.rejection_reason = payload.rejection_reason
    
    db.commit()
    db.refresh(application)

    return application