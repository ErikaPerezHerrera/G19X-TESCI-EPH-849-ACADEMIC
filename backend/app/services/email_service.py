import smtplib
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.email_template import EmailTemplate
from app.core.config import settings


def validate_email_format_and_existence(email: str) -> str:
    """
    Valida que el correo electrónico tenga un formato sintáctico correcto
    y cumpla con las reglas de negocio de PluriJob.
    """
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo electrónico es obligatorio.",
        )

    email = email.strip().lower()
    email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    if not re.match(email_regex, email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El formato del correo electrónico no es válido.",
        )
    return email


def render_template(db: Session, template_key: str, context: dict) -> tuple[str, str]:
    """
    Busca una plantilla de correo por su 'template_key' en la base de datos e
    interpola las variables del contexto en el asunto y el cuerpo del mensaje.
    """
    template = (
        db.query(EmailTemplate)
        .filter(EmailTemplate.template_key == template_key)
        .first()
    )

    if not template:
        # Fallback de emergencia por si falta la plantilla en la BD
        subject = context.get("default_subject", "Notificación de PluriJob")
        body = context.get(
            "default_body", "Hola, tienes una nueva actualización en PluriJob."
        )
    else:
        subject = template.subject
        body = template.body_text

    # Reemplazo seguro de variables estilo {{variable_name}}
    for key, value in context.items():
        placeholder = f"{{{{{key}}}}}"
        safe_value = str(value) if value is not None else ""
        subject = subject.replace(placeholder, safe_value)
        body = body.replace(placeholder, safe_value)

    # Limpieza defensiva fuera del bucle
    body = re.sub(r"\{\{.*?\}\}", "", body)
    subject = re.sub(r"\{\{.*?\}\}", "", subject)

    return subject, body


def send_email(to_email: str, subject: str, body_text: str) -> bool:
    """
    Envía un correo electrónico mediante SMTP. Si no se han configurado credenciales
    SMTP en settings, simula el envío imprimiéndolo en la consola (Mock).
    """
    # Modo desarrollo / Pruebas sin SMTP real configurado usando settings
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        print("\n==================== [EMAIL MOCK SERVICE] ====================")
        print(f" Para   : {to_email}")
        print(f" De     : {settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>")
        print(f" Asunto : {subject}")
        print(f" Cuerpo :\n{body_text}")
        print("==============================================================\n")
        return True

    try:
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
        message["To"] = to_email

        part = MIMEText(body_text, "plain", "utf-8")
        message.attach(part)

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.EMAILS_FROM_EMAIL, to_email, message.as_string())
        return True
    except Exception as e:
        print(f"Error crítico al enviar correo SMTP a {to_email}: {str(e)}")
        return False
