from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_recruiter, get_optional_current_user

from app.models.application import Application
from app.models.job import Job
from app.models.user import User

from app.schemas.job import JobCreate, JobDraftRequest, JobOut, JobReopen

from app.services.autostore_job import auto_archive_expired_closed_jobs
from app.services.email_service import send_email, render_template
from app.services.gemini_service import generate_job_draft_with_status
from app.services.skill_cache_service import ensure_skills_cached
from app.services.vector_service import (
    BGE_QUERY_INSTRUCTION,
    generate_embedding,
)

router = APIRouter(prefix="/jobs", tags=["jobs"])


## Función para sincronizar el estado de las vacantes vencidas
def _sync_expired_jobs(db: Session) -> None:
    db.execute(
        text(
            "UPDATE jobs SET status = 'expired' "
            "WHERE status = 'active' AND deadline IS NOT NULL AND deadline <= NOW()"
        )
    )
    db.commit()


## Ruta para listar vacantes con opción de filtrar por estado
@router.get("", response_model=list[JobOut])
def list_jobs(
    background_tasks: BackgroundTasks,
    status_filter: Optional[str] = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    _sync_expired_jobs(db)

    # Ejecutar la verificación de vacantes cerradas hace > 30 días
    auto_archive_expired_closed_jobs(db, background_tasks)

    is_staff = current_user is not None and getattr(current_user, "role", None) in [
        "admin",
        "recruiter",
    ]

    if not is_staff:
        status_filter = "active"

    query = db.query(Job)
    if status_filter:
        query = query.filter(Job.status == status_filter)
    return query.order_by(Job.created_at.desc()).all()


## Ruta para crear un borrador de vacante usando la API de Gemini
@router.post("/draft")
def draft_job(
    payload: JobDraftRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter),
):
    instruction = (payload.instruction or "").strip()
    source_text = (payload.source_text or "").strip()
    if not instruction and not source_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes enviar una instrucción o texto base para generar el borrador.",
        )

    return generate_job_draft_with_status(
        instruction=instruction,
        source_text=source_text,
    )


## Ruta para obtener los detalles de una vacante específica
@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Vacante no encontrada")
    return job


## Ruta para crear una nueva vacante
@router.post("", response_model=JobOut, status_code=status.HTTP_201_CREATED)
def create_job(
    payload: JobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter),
):
    raw_tech = payload.technical_skills or []
    raw_soft = payload.soft_skills or []

    ensure_skills_cached(db, list(raw_tech) + list(raw_soft))

    job = Job(
        recruiter_id=current_user.id,
        title=payload.title,
        area=payload.area,
        profile_type=payload.profile_type,
        modality=payload.modality,
        location=payload.location,
        description=payload.description,
        technical_skills=raw_tech,
        soft_skills=raw_soft,
        status=payload.status,
        deadline=payload.deadline,
        benefits=payload.benefits,
    )

    try:
        db.add(job)
        db.commit()
        db.refresh(job)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error al crear la vacante.")

    try:
        job_text_with_prompt = (
            f"{BGE_QUERY_INSTRUCTION}{job.description}" if job.description else None
        )
        job.embedding = generate_embedding(job_text_with_prompt)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La vacante se creó, pero no se pudo generar su embedding.",
        ) from exc

    try:
        db.commit()
        db.refresh(job)
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="La vacante se creó, pero no se pudo guardar su embedding.",
        ) from exc

    return job


## Ruta para cerrar una vacante
@router.patch("/{job_id}/close", response_model=JobOut)
def close_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Vacante no encontrada")

    # 1. Consultar postulaciones ANTES del commit para poder renderizar
    applications = db.query(Application).filter(Application.job_id == job.id).all()

    emails_to_notify = []
    for app in applications:
        subject, body = render_template(
            db,
            "vacancy_closed",
            {
                "candidate_name": app.candidate_email.split("@")[0],
                "job_title": job.title,
            },
        )
        emails_to_notify.append((app.candidate_email, subject, body))

    # 2. Actualizar estado y hacer commit primero
    job.status = "closed"
    db.commit()
    db.refresh(job)

    # 3. Encolar tareas de envío en segundo plano
    for email, subject, body in emails_to_notify:
        background_tasks.add_task(send_email, email, subject, body)

    return job


## Ruta para reabrir una vacante cerrada o vencida
@router.patch("/{job_id}/reopen", response_model=JobOut)
def reopen_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    payload: JobReopen,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Vacante no encontrada")

    if job.status not in ["expired", "closed"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo se pueden reabrir vacantes cerradas o vencidas.",
        )

    if payload.model_fields_set - {"deadline"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Para reabrir una vacante solo se permite actualizar la fecha límite.",
        )

    deadline = payload.deadline
    if deadline is not None:
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        if deadline <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="La nueva fecha límite debe ser posterior al momento actual.",
            )

    # 1. Obtener postulaciones y renderizar templates antes de hacer commit
    applications = db.query(Application).filter(Application.job_id == job.id).all()
    emails_to_notify = []

    for app in applications:
        subject, body = render_template(
            db,
            "status_update",
            {
                "candidate_name": "Candidato/a",
                "job_title": job.title,
                "message": "La vacante a la que te habías postulado ha sido reabierta. Tu proceso continúa activo.",
                "default_subject": f"Vacante Reabierta: {job.title}",
                "default_body": f"Hola, te informamos que la vacante '{job.title}' ha sido reabierta.",
            },
        )
        emails_to_notify.append((app.candidate_email, subject, body))

    # 2. Modificar y hacer commit
    job.deadline = deadline
    job.status = "active"

    try:
        db.commit()
        db.refresh(job)
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo reabrir la vacante.",
        ) from exc

    # 3. Encolar los correos al finalizar con éxito
    for email, subject, body in emails_to_notify:
        background_tasks.add_task(send_email, email, subject, body)

    return job


## Ruta para que un administrador cambie el estado de una vacante cerrada a 'stored'
@router.patch("/{job_id}/store", response_model=JobOut)
def store_closed_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter),
):
    if getattr(current_user, "role", None) != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado. Se requiere rol de administrador para almacenar vacantes.",
        )

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vacante no encontrada.",
        )

    if job.status != "closed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo se pueden almacenar vacantes que se encuentren en estado cerrado.",
        )

    # 1. Obtener postulaciones y renderizar templates antes de eliminarlas o hacer commit
    applications = db.query(Application).filter(Application.job_id == job.id).all()
    emails_to_notify = []

    for app in applications:
        subject, body = render_template(
            db,
            "status_update",
            {
                "candidate_name": app.candidate_email.split("@")[0],
                "job_title": job.title,
                "message": f"La vacante '{job.title}' en la que participabas ha sido archivada/eliminada. Tu postulación ha sido retirada para liberar tu cupo y ahora eres libre de participar en otro proceso de selección.",
            },
        )
        emails_to_notify.append((app.candidate_email, subject, body))

    try:
        # 2. Eliminar postulaciones y actualizar estado a stored
        db.query(Application).filter(Application.job_id == job.id).delete()
        job.status = "stored"

        db.commit()
        db.refresh(job)
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo almacenar la vacante y eliminar sus postulaciones.",
        ) from exc

    # 3. Encolar los correos al finalizar con éxito
    for email, subject, body in emails_to_notify:
        background_tasks.add_task(send_email, email, subject, body)

    return job
