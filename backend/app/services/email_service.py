import os
import smtplib
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.email_template import EmailTemplate

# Configuración SMTP desde variables de entorno (con valores por defecto seguros para desarrollo)
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAILS_FROM_EMAIL = os.getenv("EMAILS_FROM_EMAIL", "noreply@plurijob.com")
EMAILS_FROM_NAME = os.getenv("EMAILS_FROM_NAME", "PluriJob")


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

    # 1. Reemplazamos todas las variables que SÍ vienen en el contexto
    for key, value in context.items():
        placeholder = f"{{{{{key}}}}}"
        safe_value = str(value) if value is not None else ""
        subject = subject.replace(placeholder, safe_value)
        body = body.replace(placeholder, safe_value)

    # 2. Limpieza defensiva FUERA del bucle:
    # Cualquier variable opcional que no se mandó en el contexto (como {{rejection_reason}} o {{message}})
    # se borra limpiamente en lugar de dejar el texto con llaves feas.
    body = re.sub(r"\{\{.*?\}\}", "", body)
    subject = re.sub(r"\{\{.*?\}\}", "", subject)

    return subject, body


def send_email(to_email: str, subject: str, body_text: str) -> bool:
    """
    Envía un correo electrónico mediante SMTP. Si no se han configurado credenciales
    SMTP en las variables de entorno, simula el envío imprimiéndolo en la consola (Mock).
    """
    # Modo desarrollo / Pruebas sin SMTP real configurado
    if not SMTP_USER or not SMTP_PASSWORD:
        print("\n==================== [EMAIL MOCK SERVICE] ====================")
        print(f" Para   : {to_email}")
        print(f" De     : {EMAILS_FROM_NAME} <{EMAILS_FROM_EMAIL}>")
        print(f" Asunto : {subject}")
        print(f" Cuerpo :\n{body_text}")
        print("==============================================================\n")
        return True

    try:
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{EMAILS_FROM_NAME} <{EMAILS_FROM_EMAIL}>"
        message["To"] = to_email

        part = MIMEText(body_text, "plain", "utf-8")
        message.attach(part)

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(EMAILS_FROM_EMAIL, to_email, message.as_string())
        return True
    except Exception as e:
        print(f"Error crítico al enviar correo SMTP a {to_email}: {str(e)}")
        return False


def send_templated_email(
    db: Session, to_email: str, template_key: str, context: dict
) -> bool:
    """
    Función helper unificada que procesa la plantilla desde la base de datos
    con su contexto y procede a enviarla al destinatario.
    """
    subject, body_text = render_template(db, template_key, context)
    return send_email(to_email, subject, body_text)
