from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_recruiter, get_current_user
from app.models.application import Application
from app.models.job import Job
from app.models.resume import Resume
from app.models.user import User
from app.schemas.application import ApplicationCreate, ApplicationOut

router = APIRouter(prefix="", tags=["applications"])


@router.post("/jobs/{job_id}/applications", response_model=ApplicationOut, status_code=status.HTTP_201_CREATED)
def create_application(
    job_id: str,
    payload: ApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Vacante no encontrada")

    resume = db.query(Resume).filter(Resume.id == payload.resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="CV no encontrado")

    application = Application(
        job_id=job.id,
        user_id=current_user.id,
        resume_id=resume.id,
        candidate_email=payload.candidate_email or current_user.email,
        match_score=payload.match_score or 0.0,
        status="received",
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


@router.get("/applications/me", response_model=list[ApplicationOut])
def list_my_applications(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Application).filter(Application.user_id == current_user.id).order_by(Application.applied_at.desc()).all()


@router.get("/jobs/{job_id}/applications", response_model=list[ApplicationOut])
def list_job_applications(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter),
):
    return db.query(Application).filter(Application.job_id == job_id).order_by(Application.match_score.desc().nullslast()).all()
