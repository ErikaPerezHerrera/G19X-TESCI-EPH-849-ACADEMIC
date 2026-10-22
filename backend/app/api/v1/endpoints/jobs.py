from datetime import datetime, timezone

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_recruiter

from app.models.application import Application
from app.models.job import Job
from app.models.user import User

from app.schemas.job import JobCreate, JobDraftRequest, JobOut, JobReopen

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
    status_filter: Optional[str] = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
):
    _sync_expired_jobs(db)
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
            detail=(f"La vacante se creó, pero no se pudo generar su embedding: "),
        ) from exc

    try:
        db.commit()
        db.refresh(job)
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(f"La vacante se creó, pero no se pudo guardar su embedding."),
        ) from exc

    return job


## Ruta para cerrar una vacante
@router.patch("/{job_id}/close", response_model=JobOut)
def close_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Vacante no encontrada")

    job.status = "closed"
    db.commit()
    db.refresh(job)
    return job


## Ruta para reabrir una vacante cerrada o vencida (Refactorizada y unificada)
@router.patch("/{job_id}/reopen", response_model=JobOut)
def reopen_job(
    job_id: str,
    payload: JobReopen,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Vacante no encontrada")

    # Ambas (expired y closed) comparten el mismo comportamiento de reapertura
    if job.status not in ["expired", "closed"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo se pueden reabrir vacantes cerradas o vencidas.",
        )

    # Validamos que si mandan un payload, solo traiga el deadline opcionalmente
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

    return job
