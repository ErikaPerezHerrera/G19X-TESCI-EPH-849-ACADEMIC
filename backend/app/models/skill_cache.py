# Este código define el modelo ORM de SQLAlchemy para la entidad Skill_Cache

from pgvector.sqlalchemy import Vector

from sqlalchemy import Column, DateTime, Index, Integer, String, func

from app.core.database import Base


class SkillCache(Base):
    """
        Modelo ORM que representa la tabla 'skills_cache'.
        Almacena las habilidades (skills) extraídas y normalizadas para su uso en búsquedas semánticas.
    """
    __tablename__ = "skills_cache"

    # Identificador único de la habilidad en formato entero (autoincremental)
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Término original de la habilidad tal como fue extraído
    raw_term = Column(String(150), nullable=False, unique=True, index=True)

    # Término normalizado de la habilidad para búsquedas consistentes
    normalized_term = Column(String(150), nullable=False)

    # Link a la URI de la habilidad en el estándar ESCO (European Skills, Competences, Qualifications and Occupations)
    esco_uri = Column(String(255), nullable=True)

    # Vector denso de 384 dimensiones
    embedding = Column(Vector(384), nullable=True)  # Coincide con BAAI/bge-small-en-v1.5

    # Marcas de tiempo administradas por PostgreSQL
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Indices adicionales para optimizar las búsquedas y la similitud semántica
    __table_args__ = (
        Index("ix_skills_cache_raw_term_lower", func.lower(raw_term)),
        Index(
            "idx_skills_cache_embedding_hnsw",
            embedding,
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )
