from unittest.mock import patch
import pytest
from app.services.email_service import render_template, send_email
from app.models.email_template import EmailTemplate


def test_render_template_success(db_session):
    """
    Valida que la función render_template busque la plantilla en la base de datos
    e interpole correctamente las variables del contexto.
    """
    # 1. Crear la plantilla en la base de datos de prueba para asegurar que exista
    mock_template = EmailTemplate(
        template_key="status_update",
        subject="Actualización para {{candidate_name}}",
        body_text="Hola {{candidate_name}}, la vacante {{job_title}} cambió de estado. {{message}}",
    )
    db_session.add(mock_template)
    db_session.commit()

    context = {
        "candidate_name": "Ana",
        "job_title": "Ingeniera de Software",
        "message": "Tu cupo ha sido liberado.",
    }

    subject, body = render_template(db_session, "status_update", context)

    # 2. Verificar que la interpolación se realizó correctamente con los datos de la BD
    assert "Ana" in subject
    assert "Ana" in body
    assert "Ingeniera de Software" in body
    assert "Tu cupo ha sido liberado." in body


def test_render_template_fallback(db_session):
    """
    Valida que si se solicita una plantilla que no existe, utilice los valores
    de fallback definidos en el contexto de emergencia sin romper la ejecución.
    """
    context = {
        "default_subject": "Asunto de Emergencia",
        "default_body": "Cuerpo de emergencia por plantilla faltante.",
    }

    subject, body = render_template(db_session, "plantilla_inexistente_123", context)

    assert subject == "Asunto de Emergencia"
    assert body == "Cuerpo de emergencia por plantilla faltante."


def test_send_email_mock_mode():
    """
    Valida que cuando las credenciales SMTP no están configuradas (modo desarrollo/mock),
    la función de envío imprima en consola de forma segura y devuelva True.
    """
    with patch("app.services.email_service.SMTP_USER", ""), patch(
        "app.services.email_service.SMTP_PASSWORD", ""
    ):

        result = send_email(
            to_email="candidato@example.com",
            subject="Prueba Mock",
            body_text="Este es un correo de prueba simulado.",
        )
        assert result is True


def test_send_email_smtp_error_handling():
    """
    Valida que si ocurre un fallo crítico de red o excepción SMTP durante el envío real,
    la función lo capture mediante el bloque try-except y devuelva False en lugar de tumbar la API.
    """
    with patch("app.services.email_service.SMTP_USER", "usuario_smtp"), patch(
        "app.services.email_service.SMTP_PASSWORD", "password_smtp"
    ), patch(
        "smtplib.SMTP",
        side_effect=Exception("Fallo crítico de conexión con el servidor SMTP"),
    ):

        result = send_email(
            to_email="candidato@example.com",
            subject="Prueba Error",
            body_text="Este correo fallará intencionalmente.",
        )
        assert result is False


def test_render_template_removes_missing_placeholders(db_session):
    db_session.add(
        EmailTemplate(
            template_key="status_update",
            subject="Actualización",
            body_text="Hola {{candidate_name}}. {{message}}",
        )
    )
    db_session.commit()

    _, body = render_template(db_session, "status_update", {"candidate_name": "Ana"})

    assert "{{" not in body
    assert "Ana" in body
