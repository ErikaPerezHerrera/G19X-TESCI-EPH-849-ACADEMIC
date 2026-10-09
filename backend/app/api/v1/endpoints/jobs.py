from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_recruiter, get_current_user
from app.models.application import Application
from app.models.job import Job
from app.models.user import User
from app.schemas.job import JobCreate, JobOut, JobReopen

from app.services.skill_cache_service import ensure_skills_cached
from app.services.vector_service import generate_embedding
from app.services.matching_engine import recalculate_job_applications

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _sync_expired_jobs(db: Session) -> None:
    db.execute(
        text(
            "UPDATE jobs SET status = 'expired' "
            "WHERE status = 'active' AND deadline IS NOT NULL AND deadline <= NOW()"
        )
    )
    db.commit()


@router.get("", response_model=list[JobOut])
def list_jobs(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    db: Session = Depends(get_db)
):
    _sync_expired_jobs(db)
    query = db.query(Job)
    if status_filter:
        query = query.filter(Job.status == status_filter)
    return query.order_by(Job.created_at.desc()).all()


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Vacante no encontrada")
    return job

@router.post("", response_model=JobOut, status_code=status.HTTP_201_CREATED)
def create_job(
    payload: JobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter),
):
    raw_tech = payload.technical_skills or []
    raw_soft = payload.soft_skills or []

    # Verificar que las habilidades estan en la tabla de habilidades o si existen, o crearlas
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
        benefits=payload.benefits
    )

    try:
        db.add(job)
        db.commit()
        db.refresh(job)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error al crear la vacante.")

    try:
        job.embedding = generate_embedding(job.description)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                f"La vacante {job.id} se creó, pero no se pudo generar su embedding: "
                f"{exc}"
            ),
        ) from exc

    try:
        db.commit()
        db.refresh(job)
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"La vacante {job.id} se creó, pero no se pudo guardar su embedding."
            ),
        ) from exc

    return job


@router.patch("/{job_id}/close", response_model=JobOut)
def close_job(job_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_recruiter)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Vacante no encontrada")

    job.status = "closed"
    db.query(Application).filter(Application.job_id == job.id).delete(synchronize_session=False)
    db.commit()
    db.refresh(job)
    return job


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

    reopening_closed_job = job.status == "closed"
    if job.status == "expired":
        if payload.model_fields_set != {"deadline"} or payload.deadline is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Para reabrir una vacante vencida solo puedes indicar una nueva fecha límite.",
            )

        deadline = payload.deadline
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        if deadline <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="La nueva fecha límite debe ser futura.",
            )

        job.deadline = deadline
    elif job.status == "closed":
        required_fields = {
            "title",
            "area",
            "profile_type",
            "modality",
            "location",
            "description",
            "technical_skills",
            "soft_skills",
            "deadline",
            "benefits",
        }
        if not required_fields.issubset(payload.model_fields_set):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Completa los campos requeridos para reabrir la vacante cerrada.",
            )

        try:
            values = JobCreate.model_validate(
                payload.model_dump(exclude_unset=True) | {"status": "active"}
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

        deadline = values.deadline
        if deadline is not None:
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=timezone.utc)
            if deadline <= datetime.now(timezone.utc):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="La fecha límite debe ser futura.",
                )

        ensure_skills_cached(
            db, values.technical_skills + values.soft_skills
        )
        job.title = values.title
        job.area = values.area
        job.profile_type = values.profile_type
        job.modality = values.modality
        job.location = values.location
        job.description = values.description
        job.technical_skills = values.technical_skills
        job.soft_skills = values.soft_skills
        job.deadline = deadline
        job.benefits = values.benefits
    else:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo se pueden reabrir vacantes cerradas o vencidas.",
        )

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

    if reopening_closed_job:
        try:
            job.embedding = generate_embedding(job.description)
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    f"La vacante {job.id} se reabrió, pero no se pudo generar "
                    f"su embedding: {exc}"
                ),
            ) from exc

        try:
            db.commit()
            db.refresh(job)
        except Exception as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    f"La vacante {job.id} se reabrió, pero no se pudo guardar "
                    "su embedding."
                ),
            ) from exc

    try:
        recalculate_job_applications(db, job.id)
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"La vacante {job.id} se reabrió, pero no se pudo recalcular "
                "el matching de sus postulaciones."
            ),
        ) from exc

    return job
