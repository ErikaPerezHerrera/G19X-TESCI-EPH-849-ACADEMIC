from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from app.models.job import Job
from app.models.application import Application
from app.services.email_service import send_email, render_template

from fastapi import BackgroundTasks, HTTPException, status


def auto_archive_expired_closed_jobs(
    db: Session, background_tasks: Optional[BackgroundTasks] = None
):
    """
    Busca vacantes cerradas hace más de 30 días, notifica a los postulantes
    usando la plantilla 'status_update' antes de eliminar las postulaciones
    para liberar sus slots, y archiva la vacante como 'stored'.
    """
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

    # Buscar vacantes cerradas hace más de 30 días
    expired_jobs = (
        db.query(Job)
        .filter(Job.status == "closed", Job.updated_at <= thirty_days_ago)
        .all()
    )

    if not expired_jobs:
        return

    try:
        for job in expired_jobs:
            # 1. Obtener todas las postulaciones de esta vacante ANTES de borrarlas
            applications = (
                db.query(Application).filter(Application.job_id == job.id).all()
            )

            # 2. Renderizar plantillas con la sesión activa antes de borrar
            notifications = []
            for app in applications:
                subject, body = render_template(
                    db,
                    "status_update",
                    {
                        "candidate_name": app.candidate_email.split("@")[0],
                        "job_title": job.title,
                        "message": "Te informamos que la vacante ha sido archivada tras cumplirse el periodo de tiempo establecido, por lo que este proceso ha concluido.",
                    },
                )
                notifications.append((app.candidate_email, subject, body))

            # 3. Eliminar físicamente las postulaciones para liberar el slot de los candidatos
            db.query(Application).filter(Application.job_id == job.id).delete()

            # 4. Cambiar el estado de la vacante a 'stored'
            job.status = "stored"

            # Guardar cambios transaccionales primero
            db.commit()

            # 5. Encolar correos si background_tasks está disponible
            for email, subject, body in notifications:
                if background_tasks:
                    background_tasks.add_task(send_email, email, subject, body)
                else:
                    send_email(
                        email, subject, body
                    )  # Fallback síncrono si se llama sin BackgroundTasks

    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo completar el auto-archivado de las vacantes.",
        ) from exc
