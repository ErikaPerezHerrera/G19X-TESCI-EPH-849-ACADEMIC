# Este código define el modelo ORM de SQLAlchemy para la entidad Resume (Currículums / Hojas de Vida).
# Es el núcleo del motor de IA de PluriJob, ya que combina la extracción de texto,
# el almacenamiento JSON estructurado y
# el vector de 384 dimensiones (Vector(384)) para realizar búsquedas semánticas mediante pgvector.

import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class Resume(Base):
    """
    Modelo ORM que representa la tabla 'resumes'.
    Almacena los datos del CV extraídos de un PDF (texto crudo, datos parseados, habilidades)
    así como su representación vectorial (embedding) para el cálculo de coincidencia semántica.
    """

    __tablename__ = "resumes"
    __table_args__ = (
        Index(
            "uq_resumes_user_id",
            "user_id",
            unique=True,
            postgresql_where="user_id IS NOT NULL",
        ),
        Index("idx_resumes_updated_at", "updated_at"),
    )

    # Identificador único del CV en formato UUID v4
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Clave foránea que relaciona el CV con un usuario registrado (opcional para usuarios casuales)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Correo del candidato con un índice habilitado (index=True) para búsquedas rápidas
    candidate_email = Column(String(255), nullable=False, index=True)

    # Texto crudo completo extraído directamente del PDF
    raw_text = Column(Text, nullable=True)

    # Objeto JSON con la información parseada (experiencia, educación, títulos, etc.)
    parsed_data = Column(JSONB, nullable=False, default=dict, server_default="{}")

    # Lista en formato JSON con las habilidades (skills) detectadas
    extracted_skills = Column(JSONB, nullable=False, default=list, server_default="[]")

    # Vector denso de 384 dimensiones (ej: generado por un modelo all-MiniLM-L6-v2)
    # utilizado por pgvector para calcular la similitud del coseno frente a las vacantes
    embedding = Column(Vector(384), nullable=True)

    # Nombre original del archivo PDF subido por el usuario
    file_name = Column(String(255), nullable=True)

    # Fecha de expiración para limpiar automáticamente los CVs de postulantes no registrados
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Marcas de tiempo administradas por PostgreSQL
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # --- RELACIONES DE ORM ---
    # Enlace con la tabla de usuarios
    user = relationship("User", back_populates="resumes")

    # Lista de postulaciones en las que se ha adjuntado este CV
    applications = relationship("Application", back_populates="resume")
