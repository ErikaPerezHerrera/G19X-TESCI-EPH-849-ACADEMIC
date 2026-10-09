from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.skill_cache import SkillCache
from app.services.vector_service import generate_embedding as _generate_embedding

MIN_COSINE_SIMILARITY = 0.85


def generate_embedding(raw_term: Optional[str]) -> Optional[list[float]]:
    return _generate_embedding(raw_term)


def find_cosine_skill(db: Session, raw_term: Optional[str]) -> Optional[SkillCache]:
    term = (raw_term or "").strip()
    if not term:
        return None

    embedding = generate_embedding(term)
    if not embedding:
        return None

    distance = SkillCache.embedding.cosine_distance(embedding)
    query = (
        select(SkillCache)
        .where(
            SkillCache.embedding.is_not(None),
            distance <= 1 - MIN_COSINE_SIMILARITY,
        )
        .order_by(distance)
        .limit(1)
    )
    return db.scalars(query).first()
