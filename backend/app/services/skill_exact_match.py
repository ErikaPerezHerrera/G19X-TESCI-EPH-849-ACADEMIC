from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.skill_cache import SkillCache


def normalize_skill_term(raw_term: Optional[str]) -> str:
    if raw_term is None:
        return ""
    return str(raw_term).strip()


def find_exact_skill(db: Session, raw_term: Optional[str]) -> Optional[SkillCache]:
    normalized = normalize_skill_term(raw_term)
    if not normalized:
        return None

    return (
        db.query(SkillCache)
        .filter(func.lower(SkillCache.raw_term) == normalized.lower())
        .first()
    )