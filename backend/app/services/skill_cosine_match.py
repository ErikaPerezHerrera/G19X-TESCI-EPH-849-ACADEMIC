from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.skill_cache import SkillCache

_EMBEDDING_MODEL = None
MIN_COSINE_SIMILARITY = 0.85


def _get_embedding_model():
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is None:
        try:
            from fastembed import TextEmbedding
        except Exception as exc:  # pragma: no cover - depends on optional runtime dependency
            raise RuntimeError(
                "fastembed no está disponible; no se pudo generar el embedding para matching por coseno."
            ) from exc

        _EMBEDDING_MODEL = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")

    return _EMBEDDING_MODEL


def generate_embedding(raw_term: Optional[str]) -> Optional[list[float]]:
    term = (raw_term or "").strip()
    if not term:
        return None

    try:
        model = _get_embedding_model()
        embedding = next(model.embed([term]), None)
        if embedding is None:
            return None
        if hasattr(embedding, "tolist"):
            return embedding.tolist()
        return list(embedding)
    except Exception as exc:  # pragma: no cover - depends on runtime availability
        print(f"No fue posible generar el embedding para '{term}': {exc}")
        return None


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
