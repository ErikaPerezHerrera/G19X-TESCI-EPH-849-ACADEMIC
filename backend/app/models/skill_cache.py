from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, Index, Integer, String, func

from app.core.database import Base


class SkillCache(Base):
    __tablename__ = "skills_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    raw_term = Column(String(150), nullable=False, unique=True, index=True)
    normalized_term = Column(String(150), nullable=False)
    esco_uri = Column(String(255), nullable=True)
    embedding = Column(Vector(384), nullable=True)  # Coincide con BAAI/bge-small-en-v1.5
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_skills_cache_raw_term_lower", func.lower(raw_term)),
        Index(
            "idx_skills_cache_embedding_hnsw",
            embedding,
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )