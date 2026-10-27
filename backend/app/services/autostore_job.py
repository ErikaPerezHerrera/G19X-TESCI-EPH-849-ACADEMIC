from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.models.job import Job
from app.models.application import Application
from app.services.email_service import send_templated_email


def auto_archive_expired_closed_jobs(db: Session):
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

    for job in expired_jobs:
        # 1. Obtener todas las postulaciones de esta vacante ANTES de borrarlas
        applications = db.query(Application).filter(Application.job_id == job.id).all()

        # 2. Enviar correo de notificación a cada candidato usando 'status_update'
        for app in applications:
            send_templated_email(
                db,
                to_email=app.candidate_email,
                template_key="status_update",
                context={
                    "candidate_name": app.candidate_email.split("@")[0],
                    "job_title": job.title,
                    "message": "Te informamos que la vacante ha sido archivada tras cumplirse el periodo de tiempo establecido, por lo que este proceso ha concluido.",
                },
            )

        # 3. Eliminar físicamente las postulaciones para liberar el slot de los candidatos
        db.query(Application).filter(Application.job_id == job.id).delete()

        # 4. Cambiar el estado de la vacante a 'stored' (archivada / plantilla)
        job.status = "stored"

    # Guardar todos los cambios de forma transaccional en la base de datos
    db.commit()
