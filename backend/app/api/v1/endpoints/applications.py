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


## Ruta para crear una postulación a una vacante
@router.post(
    "/jobs/{job_id}/applications",
    response_model=ApplicationOut,
    status_code=status.HTTP_201_CREATED,
)

## Crear postulación a una vacante
def create_application(
    job_id: UUID,
    payload: ApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
    ):
    ## revisa si el rol del usuario actual es "registered" o "casual", si no lo es, lanza un error 403
    if current_user is not None and current_user.role not in ("registered", "casual"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los candidatos pueden postularse.",
        )
    # Busca si la vacante existe y si está activa y dentro del plazo de postulación
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

    # Busca el CV asociado al ID proporcionado en la solicitud
    resume = db.query(Resume).filter(Resume.id == payload.resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="CV no encontrado")

    # Verifica que el correo electrónico proporcionado en la solicitud coincida con el correo electrónico del CV
    candidate_email = str(payload.candidate_email).lower()
    if candidate_email != resume.candidate_email.lower():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El correo de la postulación debe coincidir con el correo del CV.",
        )
    # Verifica que el usuario actual (si existe) sea el propietario del CV, o que el CV no tenga un propietario si el usuario no está autenticado
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

    # LÍMITE DE POSTULACIONES: Comprobar si el usuario ya tiene 3 o más postulaciones activas
    active_query = db.query(Application).filter(
        (Application.user_id == current_user.id)
        if current_user
        else (func.lower(Application.candidate_email) == candidate_email)
    )
    # Opcional: si manejas un estatus específico para filtrar las activas (ej: excluyendo rechazadas por si acaso queda alguna)
    # active_query = active_query.filter(Application.status != "rejected")

    active_applications_count = active_query.count()
    if active_applications_count >= 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Has alcanzado el límite máximo de 3 postulaciones activas simultáneas. Debes cancelar alguna para postularte a otra.",
        )

    # Verifica si ya existe una postulación para la misma vacante y correo electrónico
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

    # Extrae las habilidades técnicas y blandas del CV y asegura que estén en la caché de habilidades, si no, las agrega. Luego crea la postulación y calcula el puntaje de coincidencia.
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


## Ruta para listar postulaciones del usuario autenticado
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


## Ruta para que el candidato cancele (elimine) su postulación
@router.delete("/applications/{application_id}", status_code=status.HTTP_200_OK)
def cancel_application(
    application_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ):
    # Buscar la postulación
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Postulación no encontrada.",
        )

    # Validar que pertenezca al usuario autenticado (si la postulación tiene user_id asociado)
    # O validar por correo si el usuario es casual/registrado y coincide con su email
    if application.user_id and application.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para cancelar esta postulación.",
        )
    
    # Eliminar físicamente la postulación para liberar el cupo y evitar recálculos de match
    db.delete(application)
    db.commit()

    return {"message": "Postulación cancelada y eliminada correctamente."}


## Ruta específica en la que el usuario autenticado es reclutador, para listar postulaciones de una vacante
@router.get("/jobs/{job_id}/applications", response_model=list[ApplicationOut])
def list_job_applications(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter),
    ):
    return (
        db.query(Application)
        .options(
            joinedload(Application.resume)
        )  # <--- Carga los datos del CV/Resume asociado
        .filter(Application.job_id == job_id)
        .order_by(Application.match_score.desc().nullslast())
        .all()
    )

## Ruta específica en la que el usuario autenticado es reclutador, para descartar y eliminar una postulación
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

    # 1. Capturamos los datos clave antes de eliminar la postulación
    candidate_email = application.candidate_email
    rejection_reason = payload.rejection_reason

    # TODO: Aquí se integrará después la función para enviar el correo electrónico
    # Ejemplo: send_rejection_email(candidate_email, rejection_reason)

    try:
        # 2. Eliminamos físicamente la postulación de la base de datos para liberar el cupo y evitar recálculos
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
