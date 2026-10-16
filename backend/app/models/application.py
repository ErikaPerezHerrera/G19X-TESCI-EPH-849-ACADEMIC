# Este código representa el modelo ORM de SQLAlchemy para la entidad Application (Postulaciones)
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Application(Base):
    """
    Modelo ORM que representa la tabla 'applications'.
    Vincula a un candidato (mediante su CV y/o usuario registrado) con una oferta de empleo,
    almacenando la puntuación de coincidencia (match_score), el desglose explicativo y el estado.
    """

    __tablename__ = "applications"

    # --- CONFIGURACIÓN DE TABLA: RESTRICCIONES E ÍNDICES ---
    __table_args__ = (
        # Valida en base de datos que match_score sea un porcentaje válido entre 0 y 100
        CheckConstraint(
            "match_score IS NULL OR (match_score >= 0 AND match_score <= 100)",
            name="chk_applications_match_score",
        ),
        # Índice para ordenar a los candidatos de una vacante por su puntuación de matching
        Index("idx_applications_job_score", "job_id", "match_score"),
        # Índice para acelerar la consulta del historial de postulaciones de un candidato
        Index("idx_applications_user_applied_at", "user_id", "applied_at"),
        # Índice para filtrar candidatos por estado dentro del tablero del reclutador (ej: 'under_review', 'shortlisted')
        Index("idx_applications_job_status", "job_id", "status"),
    )

    # Identificador único de la postulación (UUID v4)
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Claves foráneas: Vinculación con la oferta, el usuario (opcional) y el CV utilizado
    job_id = Column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resume_id = Column(
        UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="RESTRICT"), nullable=False
    )

    # Correo de contacto del candidato
    candidate_email = Column(String(255), nullable=False, index=True)

    # Puntuación final de coincidencia (0.00 a 100.00)
    match_score = Column(Numeric(5, 2), nullable=True)

    # Indicador de alerta para el reclutador si el candidato excede los requisitos del puesto
    is_overqualified = Column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    # Análisis complementario en formato JSONB generado por la IA (puntos fuertes, recomendaciones)
    ai_analysis = Column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    # Desglose explicativo en formato JSONB (coincidencias léxicas, habilidades encontradas/faltantes, score vectorial)
    match_details = Column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    # Estado actual de la postulación (ej: 'received', 'under_review', 'shortlisted', 'rejected')
    status = Column(
        ENUM(
            "received",
            "under_review",
            "shortlisted",
            "interview_scheduled",
            "rejected",
            "hired",
            name="application_status_enum",
        ),
        nullable=False,
        default="received",
        server_default="received",
    )

    # Motivo opcional registrado al descartar/rechazar una postulación
    rejection_reason = Column(Text, nullable=True)

    # Marcas de tiempo gestionadas por la base de datos
    applied_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # --- RELACIONES DE ORM ---
    job = relationship("Job", back_populates="applications")
    user = relationship("User", back_populates="applications")
    resume = relationship("Resume", back_populates="applications")
