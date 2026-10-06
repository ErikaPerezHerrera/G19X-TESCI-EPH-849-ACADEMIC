from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_recruiter, get_current_user
from app.models.job import Job
from app.models.user import User
from app.schemas.job import JobCreate, JobOut

from app.services.skill_cache_service import ensure_skills_cached

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[JobOut])
def list_jobs(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    db: Session = Depends(get_db)
):
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
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    return job


@router.patch("/{job_id}/close", response_model=JobOut)
def close_job(job_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_recruiter)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Vacante no encontrada")
    if job.recruiter_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes permiso para cerrar esta vacante")
    job.status = "closed"
    db.commit()
    db.refresh(job)
    return job


@router.patch("/{job_id}/reopen", response_model=JobOut)
def reopen_job(job_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_recruiter)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Vacante no encontrada")
    if job.recruiter_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes permiso para reabrir esta vacante")
    job.status = "active"
    db.commit()
    db.refresh(job)
    return job
