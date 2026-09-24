from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, Integer, String, func

from app.core.database import Base


class SkillCache(Base):
    __tablename__ = "skills_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    raw_term = Column(String(150), nullable=False, unique=True)
    normalized_term = Column(String(150), nullable=False)
    esco_uri = Column(String(255), nullable=True)
    embedding = Column(Vector(384), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)