from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks

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
from app.services.email_service import send_email, render_template

router = APIRouter(prefix="", tags=["applications"])


def _validate_recruiter_or_admin(current_user: User):
    """Valida que el usuario tenga rol de reclutador o administrador."""
    if current_user.role not in ("recruiter", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado. Se requiere rol de reclutador o administrador.",
        )


def _validate_job_active_for_applications(job: Job):
    """Bloquea cambios si la vacante está cerrada o archivada (409 Conflict)."""
    if job and job.status in ("closed", "stored"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se pueden realizar cambios de estado en postulaciones de una vacante cerrada o archivada.",
        )


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
    background_tasks: BackgroundTasks,
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

    # Validar si ya existe una postulación previa para esta vacante con este correo
    existing_application = (
        db.query(Application)
        .filter(
            Application.job_id == job_id,
            Application.candidate_email == payload.candidate_email,
        )
        .first()
    )

    if existing_application:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una postulación activa para esta vacante con este correo electrónico.",
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

    ## Calcular el match
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

    subject, body = render_template(
        db,
        "application_received",
        {
            "candidate_name": application.candidate_email.split("@")[0],
            "job_title": job.title,
            "match_score": match_percentage,
        },
    )

    background_tasks.add_task(send_email, application.candidate_email, subject, body)

    return application


## Ruta para que el candidato cancele su postulación
@router.delete("/applications/{application_id}", status_code=status.HTTP_200_OK)
def cancel_application(
    application_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="La postulación no existe."
        )

    job = db.query(Job).filter(Job.id == application.job_id).first()
    _validate_job_active_for_applications(job)

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

    candidate_email = application.candidate_email
    job_title = job.title if job else "la vacante"

    subject, body = render_template(
        db,
        "status_update",
        {
            "candidate_name": candidate_email.split("@")[0],
            "job_title": job_title,
            "message": f"Has cancelado exitosamente tu postulación a la vacante '{job_title}'. Tu cupo ha sido liberado y eres libre de participar en otro proceso de selección.",
        },
    )

    db.delete(application)
    db.commit()

    background_tasks.add_task(send_email, candidate_email, subject, body)

    return {"message": "Postulación cancelada con éxito"}


## --- RUTAS DE RECLUTADOR ---


## Listar postulaciones de una vacante
@router.get("/jobs/{job_id}/applications", response_model=list[ApplicationOut])
def list_job_applications(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter),
):
    _validate_recruiter_or_admin(current_user)
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
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter),
):
    _validate_recruiter_or_admin(current_user)

    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Postulación no encontrada.")

    job = db.query(Job).filter(Job.id == application.job_id).first()
    _validate_job_active_for_applications(job)

    valid_previous_states = ["received", "application_received"]
    if application.status not in valid_previous_states:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La postulación debe encontrarse en estado 'application_received' para pasar a revisión.",
        )

    application.status = "application_under_review"
    db.commit()
    db.refresh(application)

    subject, body = render_template(
        db,
        "application_under_review",
        {
            "candidate_name": application.candidate_email.split("@")[0],
            "job_title": job.title if job else "la vacante",
        },
    )

    background_tasks.add_task(send_email, application.candidate_email, subject, body)

    return application


## Ruta para programar entrevista
@router.patch("/applications/{application_id}/interview", response_model=ApplicationOut)
def schedule_interview_application(
    application_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter),
):
    _validate_recruiter_or_admin(current_user)

    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Postulación no encontrada.")

    job = db.query(Job).filter(Job.id == application.job_id).first()
    _validate_job_active_for_applications(job)

    if application.status != "application_under_review":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La postulación debe encontrarse en estado 'application_under_review' para programar una entrevista.",
        )

    application.status = "interview_scheduled"
    db.commit()
    db.refresh(application)

    subject, body = render_template(
        db,
        "interview_progress",
        {
            "candidate_name": application.candidate_email.split("@")[0],
            "job_title": job.title if job else "la vacante",
        },
    )

    background_tasks.add_task(send_email, application.candidate_email, subject, body)

    return application


## Ruta para contratar candidato (y cerrar vacante)
@router.patch("/applications/{application_id}/hire", response_model=ApplicationOut)
def hire_application(
    application_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter),
):
    _validate_recruiter_or_admin(current_user)

    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Postulación no encontrada.")

    job = db.query(Job).filter(Job.id == application.job_id).first()
    _validate_job_active_for_applications(job)

    if application.status != "interview_scheduled":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La postulación debe encontrarse en estado 'interview_scheduled' para poder contratar al candidato.",
        )

    existing_hired = (
        db.query(Application)
        .filter(
            Application.job_id == application.job_id,
            Application.status == "hired",
            Application.id != application.id,
        )
        .first()
    )
    if existing_hired:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un candidato contratado para esta vacante.",
        )

    application.status = "hired"

    if job:
        job.status = "closed"

    # 1. Renderizar plantilla del candidato contratado antes del commit
    subject_hired, body_hired = render_template(
        db,
        "hired",
        {
            "candidate_name": application.candidate_email.split("@")[0],
            "job_title": job.title if job else "la vacante",
        },
    )

    # 2. Consultar y renderizar plantillas de los demás postulantes antes del commit
    other_applications = (
        db.query(Application)
        .filter(
            Application.job_id == application.job_id, Application.id != application.id
        )
        .all()
    )

    other_emails_to_notify = []
    for app in other_applications:
        subject_closed, body_closed = render_template(
            db,
            "vacancy_closed",
            {
                "candidate_name": app.candidate_email.split("@")[0],
                "job_title": job.title if job else "la vacante",
            },
        )
        other_emails_to_notify.append(
            (app.candidate_email, subject_closed, body_closed)
        )

    # 3. Hacer el commit primero
    db.commit()
    db.refresh(application)

    # 4. Encolar las tareas en segundo plano después del commit
    background_tasks.add_task(
        send_email, application.candidate_email, subject_hired, body_hired
    )
    for email, sub, body in other_emails_to_notify:
        background_tasks.add_task(send_email, email, sub, body)

    return application


## Ruta para descartar candidato
@router.patch("/applications/{application_id}/reject", status_code=status.HTTP_200_OK)
def reject_application(
    application_id: UUID,
    background_tasks: BackgroundTasks,
    payload: ApplicationReject,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter),
):
    _validate_recruiter_or_admin(current_user)

    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Postulación no encontrada.",
        )

    job = db.query(Job).filter(Job.id == application.job_id).first()
    _validate_job_active_for_applications(job)

    candidate_email = application.candidate_email
    job_title = job.title if job else "la vacante"

    rejection_reason = (
        f" Motivo del descarte: {payload.rejection_reason}."
        if payload.rejection_reason
        else ""
    )

    # 1. Renderizar plantilla con la sesión activa antes de eliminar
    subject, body = render_template(
        db,
        "application_rejected",
        {
            "candidate_name": candidate_email.split("@")[0],
            "job_title": job_title,
            "rejection_reason": rejection_reason,
        },
    )

    try:
        # 2. Hacer commit / delete primero
        db.delete(application)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo procesar el descarte de la postulación.",
        ) from exc

    # 3. Encolar el correo al finalizar con éxito
    background_tasks.add_task(send_email, candidate_email, subject, body)

    return {
        "message": "Postulación rechazada y eliminada correctamente.",
        "candidate_email": candidate_email,
        "rejection_reason": payload.rejection_reason,
    }
