## Este código define el modelo ORM de SQLAlchemy para la entidad EmailTemplate (Plantillas de Correo Electrónico).
from sqlalchemy import BigInteger, Boolean, Column, DateTime, String, Text, func

from app.core.database import Base


class EmailTemplate(Base):
    """
    Modelo ORM que representa la tabla 'email_templates'.
    Guarda las plantillas dinámicas utilizadas para enviar correos transaccionales
    (confirmación de registro, notificación de postulación, cambio de estado, etc.).
    """

    __tablename__ = "email_templates"

    # Identificador único de la plantilla (autoincremental de tipo Entero)
    id = Column(BigInteger, primary_key=True, index=True)

    # Clave de identificación única en código (ej: 'welcome_email', 'application_received', 'status_changed').
    # Es única (unique=True) para poder buscarla directamente por su nombre de clave.
    template_key = Column(String(50), unique=True, nullable=False)

    # Asunto del correo electrónico (soporta variables dinámicas como "Hola {candidate_name}")
    subject = Column(String(200), nullable=False)

    # Cuerpo principal del correo en formato texto o HTML
    body_text = Column(Text, nullable=False)

    # Bandera que indica si la plantilla es del sistema (por defecto).
    # Evita que plantillas críticas del flujo de la aplicación sean eliminadas por error desde un panel de administración.
    is_system_fallback = Column(Boolean, nullable=False, default=False)

    # Marcas de tiempo de creación y última modificación administradas por PostgreSQL
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
