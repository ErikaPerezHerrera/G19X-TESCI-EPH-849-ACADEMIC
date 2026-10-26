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
from app.services.email_service import send_templated_email

router = APIRouter(prefix="", tags=["applications"])


## --- RUTAS ESPECÍFICAS DE CANDIDATO (Primero las fijas) ---


## Ruta para listar postulaciones del usuario autenticado
@router.get("/applications/me", response_model=list[ApplicationOut])
def list_my_applications(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    return (
        db.query(Application)
        .options(joinedload(Application.job))
        .filter(Application.user_id == current_user.id)
        .all()
    )


## Ruta para crear una postulación a una vacante
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

    active_query = db.query(Application).filter(
        (Application.user_id == current_user.id)
        if current_user
        else (func.lower(Application.candidate_email) == candidate_email)
    )

    if active_query.count() >= 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Has alcanzado el límite máximo de 3 postulaciones activas simultáneas.",
        )

    existing_application = (
        db.query(Application)
        .filter(
            Application.id
            == job.id,  # Ojo con esto, mantenemos tu lógica original de job_id
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

    application = Application(
        job_id=job.id,
        user_id=current_user.id if current_user is not None else None,
        resume_id=resume.id,
        candidate_email=candidate_email,
        match_score=None,
        status="application_received",
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

    match_percentage = (
        f"{round(application.match_score)}%"
        if application.match_score is not None
        else "N/A"
    )

    send_templated_email(
        db,
        to_email=application.candidate_email,
        template_key="application_received",
        context={
            "candidate_name": application.candidate_email.split("@")[0],
            "job_title": job.title,
            "match_score": match_percentage,
        },
    )

    return application


## Ruta para que el candidato cancele su postulación
@router.delete("/applications/{application_id}", status_code=status.HTTP_200_OK)
def cancel_application(
    application_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="La postulación no existe."
        )

    is_owner = False
    if application.user_id and str(application.user_id) == str(current_user.id):
        is_owner = True
    elif (
        application.candidate_email
        and application.candidate_email.lower() == current_user.email.lower()
    ):
        is_owner = True

    if not is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para cancelar esta postulación.",
        )

    db.delete(application)
    db.commit()
    return {"message": "Postulación cancelada con éxito"}


## --- RUTAS DE RECLUTADOR ---


## Listar postulaciones de una vacante
@router.get("/jobs/{job_id}/applications", response_model=list[ApplicationOut])
def list_job_applications(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter),
):
    return (
        db.query(Application)
        .options(joinedload(Application.resume))
        .filter(Application.job_id == job_id)
        .order_by(Application.match_score.desc().nullslast())
        .all()
    )


## Ruta para marcar CV como visto (application_under_review)
@router.patch("/applications/{application_id}/view", response_model=ApplicationOut)
def mark_application_as_viewed(
    application_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter),
):
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Postulación no encontrada.")

    initial_states = ["received", "application_received"]
    if application.status in initial_states:
        application.status = "application_under_review"
        db.commit()
        db.refresh(application)

        job = db.query(Job).filter(Job.id == application.job_id).first()
        send_templated_email(
            db,
            to_email=application.candidate_email,
            template_key="application_under_review",
            context={
                "candidate_name": application.candidate_email.split("@")[0],
                "job_title": job.title if job else "la vacante",
            },
        )

    return application


## Ruta para programar entrevista
@router.patch("/applications/{application_id}/interview", response_model=ApplicationOut)
def schedule_interview_application(
    application_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter),
):
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Postulación no encontrada.")

    application.status = "interview_scheduled"
    db.commit()
    db.refresh(application)

    job = db.query(Job).filter(Job.id == application.job_id).first()
    send_templated_email(
        db,
        to_email=application.candidate_email,
        template_key="interview_scheduled",
        context={
            "candidate_name": application.candidate_email.split("@")[0],
            "job_title": job.title if job else "la vacante",
        },
    )
    return application


## Ruta para contratar candidato (y cerrar vacante)
@router.patch("/applications/{application_id}/hire", response_model=ApplicationOut)
def hire_application(
    application_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter),
):
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Postulación no encontrada.")

    application.status = "hired"

    job = db.query(Job).filter(Job.id == application.job_id).first()
    if job:
        job.status = "closed"

    db.commit()
    db.refresh(application)

    # 1. Notificar al candidato contratado
    send_templated_email(
        db,
        to_email=application.candidate_email,
        template_key="hired",
        context={
            "candidate_name": application.candidate_email.split("@")[0],
            "job_title": job.title if job else "la vacante",
        },
    )

    # 2. Notificar a los demás postulantes
    other_applications = (
        db.query(Application)
        .filter(
            Application.job_id == application.job_id, Application.id != application.id
        )
        .all()
    )

    for other_app in other_applications:
        send_templated_email(
            db,
            to_email=other_app.candidate_email,
            template_key="vacancy_closed",
            context={
                "candidate_name": other_app.candidate_email.split("@")[0],
                "job_title": job.title if job else "la vacante",
            },
        )

    return application


## Ruta para descartar candidato
@router.patch("/applications/{application_id}/reject", status_code=status.HTTP_200_OK)
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

    job = db.query(Job).filter(Job.id == application.job_id).first()
    candidate_email = application.candidate_email

    rejection_reason = (
        f"\nMotivo del descarte: {payload.rejection_reason}"
        if payload.rejection_reason
        else ""
    )

    send_templated_email(
        db,
        to_email=candidate_email,
        template_key="application_rejected",
        context={
            "candidate_name": candidate_email.split("@")[0],
            "job_title": job.title if job else "la vacante",
            "rejection_reason": rejection_reason,
        },
    )

    try:
        db.delete(application)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo procesar el descarte de la postulación.",
        ) from exc

    return {
        "message": "Postulación rechazada y eliminada correctamente.",
        "candidate_email": candidate_email,
        "rejection_reason": rejection_reason,
    }
