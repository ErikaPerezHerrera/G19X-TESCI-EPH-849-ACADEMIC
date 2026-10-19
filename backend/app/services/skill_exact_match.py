from typing import Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.skill_cache import SkillCache

## Función que quita espacios extra antes y despues del término que se le da
def normalize_skill_term(raw_term: Optional[str]) -> str:
    if raw_term is None:
        return ""
    return str(raw_term).strip()

## Función que normaliza la habilidad y la busca en la base de datos para contabilizarla como término que coincide. Llama a la función descrita arriba.
def find_exact_skill(db: Session, raw_term: Optional[str]) -> Optional[SkillCache]:
    normalized = normalize_skill_term(raw_term)
    if not normalized:
        return None

    return (
        db.query(SkillCache)
        .filter(
            or_(
                func.lower(SkillCache.raw_term) == normalized.lower(),
                func.lower(SkillCache.normalized_term) == normalized.lower(),
            )
        )
        .first()
    )