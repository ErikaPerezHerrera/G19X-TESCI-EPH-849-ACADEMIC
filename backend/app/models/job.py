# Este código define el modelo ORM de SQLAlchemy para la entidad Job (Vacantes de Empleo).
# Es una de las tablas centrales del sistema, pues almacena las ofertas publicadas por los reclutadores
# con sus requerimientos, modalidades y fechas límite.

import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Job(Base):
    """
    Modelo ORM que representa la tabla 'jobs'.
    Almacena las ofertas laborales o vacantes creadas por los reclutadores,
    incluyendo detalles del puesto, requerimientos (skills) y estado de la vacante.
    """

    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint(
            "deadline IS NULL OR deadline > created_at",
            name="chk_jobs_deadline_after_creation",
        ),
        CheckConstraint(
            "modality = 'remoto' OR NULLIF(BTRIM(location), '') IS NOT NULL",
            name="chk_jobs_location_by_modality",
        ),
        Index("idx_jobs_recruiter", "recruiter_id"),
        Index("idx_jobs_status", "status"),
        Index("idx_jobs_area_modality", "area", "modality"),
        Index("idx_jobs_deadline", "deadline"),
        Index("idx_jobs_created_at", "created_at"),
    )

    # Identificador único de la vacante basado en UUID v4
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Clave foránea que vincula la oferta con el reclutador que la creó (tabla 'users')
    recruiter_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Título o nombre de la oferta laboral (ej: "Desarrollador Backend Python Senior")
    title = Column(String(150), nullable=False)

    # Área profesional u departamental (ej: "Tecnología", "Recursos Humanos")
    area = Column(String(100), nullable=False)

    # Perfil académico o profesional requerido para la vacante.
    profile_type = Column(Text, nullable=False)

    # Modality de trabajo (ej: "presencial", "remoto", "híbrido")
    modality = Column(
        ENUM(
            "presencial",
            "remoto",
            "hibrido",
            name="job_modality_enum",
        ),
        nullable=False,
        default="presencial",
        server_default="presencial",
    )

    # Ubicación geográfica de la vacante (ej: "Ciudad de México, México" o Nulo si es 100% remoto)
    location = Column(String(150), nullable=True)

    # Descripción completa y detallada de la oferta de trabajo
    description = Column(Text, nullable=False)

    # Lista de habilidades técnicas en formato JSON (ej: ["Python", "FastAPI", "PostgreSQL"])
    technical_skills = Column(JSONB, nullable=False, default=list, server_default="[]")

    # Lista de habilidades blandas en formato JSON (ej: ["Comunicación", "Trabajo en equipo"])
    soft_skills = Column(JSONB, nullable=False, default=list, server_default="[]")

    embedding = Column(Vector(384), nullable=True)

    # Estado de la vacante (ej: 'active', 'closed', 'paused')
    status = Column(
        ENUM("draft", "active", "closed", "expired", name="job_status_enum"),
        nullable=False,
        default="draft",
        server_default="draft",
    )

    # Fecha y hora límite para recibir postulaciones (opcional)
    deadline = Column(DateTime(timezone=True), nullable=True)

    # Marcas de tiempo gestionadas por PostgreSQL para la creación y modificación
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Descripción completa y detallada de la oferta de trabajo
    benefits = Column(Text, nullable=True)

    # --- RELACIONES DE ORM ---
    # Permite acceder al objeto del reclutador creador (ej: job.recruiter.email)
    recruiter = relationship("User", back_populates="jobs")

    # Lista de postulaciones que ha recibido esta vacante (ej: job.applications)
    applications = relationship("Application", back_populates="job")
