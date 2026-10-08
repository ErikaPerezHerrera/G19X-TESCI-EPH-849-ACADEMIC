import asyncio
import logging
from typing import Dict, Iterable, List, Optional

import httpx
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.skill_cache import SkillCache
from app.services.skill_cosine_match import find_cosine_skill, generate_embedding
from app.services.skill_exact_match import find_exact_skill

ESCO_API_SEARCH_URL = "https://ec.europa.eu/esco/api/search"
logger = logging.getLogger(__name__)


def normalize_skill_term(raw_term: Optional[str]) -> str:
    if raw_term is None:
        return ""
    return str(raw_term).strip()


def query_esco_api(term: str) -> Optional[Dict[str, str]]:
    """Consulta la API de ESCO buscando coincidencia exacta o por inclusión."""
    clean_term = normalize_skill_term(term).lower()
    if len(clean_term) < 2:
        return None

    params = {"text": clean_term, "type": "skill", "language": "es", "limit": 5}

    try:
        with httpx.Client(timeout=3.5) as client:
            response = client.get(ESCO_API_SEARCH_URL, params=params)
            if response.status_code != 200:
                return None

            data = response.json()
            results = data.get("_embedded", {}).get("results", [])

            for item in results:
                title = str(item.get("title", "")).strip()
                title_lower = title.lower()
                uri = str(item.get("uri", "") or "")

                if title_lower == clean_term:
                    return {"normalized_term": title, "esco_uri": uri}

                if clean_term in title_lower and len(clean_term) >= 3:
                    return {"normalized_term": title, "esco_uri": uri}
    except Exception as exc:
        print(f"Error al consultar API externa de ESCO para '{term}': {exc}")

    return None


async def _query_esco_api_async(
    client: httpx.AsyncClient,
    term: str,
    semaphore: asyncio.Semaphore,
) -> Optional[Dict[str, str]]:
    params = {"text": term, "type": "skill", "language": "es", "limit": 5}
    try:
        async with semaphore:
            response = await client.get(ESCO_API_SEARCH_URL, params=params)
        if response.status_code != 200:
            logger.warning(
                "ESCO devolvió HTTP %s al buscar una habilidad.",
                response.status_code,
            )
            return None

        results = response.json().get("_embedded", {}).get("results", [])
        normalized_term = term.strip().casefold()
        candidates = [
            item
            for item in results
            if isinstance(item, dict) and str(item.get("title", "")).strip()
        ]
        selected = next(
            (
                item
                for item in candidates
                if str(item["title"]).strip().casefold() == normalized_term
            ),
            None,
        )
        if selected is None:
            selected = next(
                (
                    item
                    for item in candidates
                    if normalized_term in str(item["title"]).strip().casefold()
                ),
                candidates[0] if candidates else None,
            )
        if selected is None:
            return None

        return {
            "normalized_term": str(selected["title"]).strip(),
            "esco_uri": str(selected.get("uri") or "").strip(),
        }
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        logger.warning("No se pudo consultar ESCO para una habilidad: %s", exc)
        return None


async def cache_extracted_skill_terms(
    db: Session, skill_terms: Iterable[str]
) -> List[SkillCache]:
    """Cache exact resume skill terms, resolving uncached terms through ESCO."""
    unique_terms: dict[str, str] = {}
    for term in skill_terms or []:
        if isinstance(term, str):
            clean_term = normalize_skill_term(term)
            if clean_term:
                unique_terms.setdefault(clean_term.casefold(), clean_term)

    cached_by_term: dict[str, SkillCache] = {}
    uncached_terms: list[str] = []
    for key, term in unique_terms.items():
        cached = find_exact_skill(db, term)
        if cached is None:
            uncached_terms.append(term)
        else:
            cached_by_term[key] = cached

    if uncached_terms:
        semaphore = asyncio.Semaphore(5)
        async with httpx.AsyncClient(timeout=3.5) as client:
            esco_results = await asyncio.gather(
                *(
                    _query_esco_api_async(client, term, semaphore)
                    for term in uncached_terms
                )
            )
    else:
        esco_results = []

    for term, esco_data in zip(uncached_terms, esco_results):
        normalized_term = (
            esco_data.get("normalized_term", term) if esco_data else term
        )
        esco_uri = (esco_data.get("esco_uri") or None) if esco_data else None
        embedding = await asyncio.to_thread(generate_embedding, normalized_term)
        cached = _upsert_skill_record(
            db=db,
            raw_term=term,
            normalized_term=normalized_term,
            esco_uri=esco_uri,
            embedding=embedding,
        )
        if cached is None:
            raise RuntimeError(f"No se pudo guardar la habilidad extraída: {term}")
        cached_by_term[term.casefold()] = cached

    return [cached_by_term[key] for key in unique_terms if key in cached_by_term]


def _upsert_skill_record(
    db: Session,
    raw_term: str,
    normalized_term: str,
    esco_uri: Optional[str] = None,
    embedding: Optional[list[float]] = None,
) -> Optional[SkillCache]:
    skill = SkillCache(
        raw_term=raw_term,
        normalized_term=normalized_term,
        esco_uri=esco_uri,
        embedding=embedding,
    )
    try:
        with db.begin_nested():
            db.add(skill)
            db.flush()
        return skill
    except IntegrityError:
        existing = (
            db.query(SkillCache)
            .filter(func.lower(SkillCache.raw_term) == raw_term.lower())
            .first()
        )
        if existing is None and esco_uri:
            existing = (
                db.query(SkillCache)
                .filter(SkillCache.esco_uri == esco_uri)
                .first()
            )
        return existing


def get_or_fetch_skill(db: Session, raw_term: str):
    clean_term = normalize_skill_term(raw_term)
    if not clean_term:
        return None

    cached = find_exact_skill(db, clean_term)
    if cached:
        if cached.embedding is None:
            embedding = generate_embedding(cached.normalized_term) or generate_embedding(
                clean_term
            )
            if embedding is not None:
                cached.embedding = embedding
                db.flush()
        return cached

    cached = find_cosine_skill(db, clean_term)
    if cached:
        return cached

    esco_data = query_esco_api(clean_term)
    normalized_term = (
        esco_data.get("normalized_term") if esco_data else clean_term
    )
    esco_uri = esco_data.get("esco_uri") if esco_data else None
    embedding = generate_embedding(normalized_term) or generate_embedding(clean_term)

    existing = (
        db.query(SkillCache)
        .filter(func.lower(SkillCache.raw_term) == clean_term.lower())
        .first()
    )
    if existing:
        return existing

    return _upsert_skill_record(
        db=db,
        raw_term=clean_term,
        normalized_term=normalized_term,
        esco_uri=esco_uri,
        embedding=embedding,
    )


def ensure_skills_cached(db: Session, skills_list: Iterable[str]) -> List[SkillCache]:
    cached_entries: List[SkillCache] = []
    for skill in skills_list or []:
        if not isinstance(skill, str):
            continue
        normalized = normalize_skill_term(skill)
        if not normalized:
            continue
        cached = get_or_fetch_skill(db, normalized)
        if cached is not None:
            cached_entries.append(cached)
    return cached_entries


def normalize_skills_list(db: Session, skills_list: list[str]) -> list[str]:
    """Toma una lista de habilidades en texto plano y las normaliza usando la BD/ESCO."""
    normalized_skills: list[str] = []
    for skill in skills_list or []:
        if not isinstance(skill, str):
            continue
        skill_entry = get_or_fetch_skill(db, skill)
        if skill_entry is not None:
            normalized_skills.append(skill_entry.normalized_term)
        else:
            normalized_skills.append(skill.strip())
    return normalized_skills
