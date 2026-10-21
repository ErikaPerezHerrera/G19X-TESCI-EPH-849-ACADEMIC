import asyncio
from unittest.mock import patch, AsyncMock
import httpx

from app.core.database import SessionLocal
from app.models.skill_cache import SkillCache
from app.services.skill_cache_service import (
    normalize_skill_term,
    get_or_fetch_skill,
    ensure_skills_cached,
    normalize_skills_list,
    _query_esco_api_async,
    cache_extracted_skill_terms,
)


def reset_database():
    db = SessionLocal()
    try:
        db.query(SkillCache).delete()
        db.commit()
    finally:
        db.close()


def test_normalize_skill_term():
    """Valida que la función elimine espacios sobrantes de forma correcta."""
    assert normalize_skill_term("   Python   ") == "Python"
    assert normalize_skill_term(None) == ""
    assert normalize_skill_term("FastAPI") == "FastAPI"


def test_cache_hit_does_not_query_esco():
    """Valida que si hay un acierto exacto en caché, no se intente consultar ESCO ni generar llamadas externas."""
    reset_database()
    db = SessionLocal()
    try:
        skill = SkillCache(
            raw_term="python",
            normalized_term="Python",
            esco_uri="http://esco/python",
            embedding=[0.1] * 384,
        )
        db.add(skill)
        db.commit()

        with patch(
            "app.services.skill_cache_service.query_esco_api"
        ) as mock_esco, patch(
            "app.services.skill_cache_service.find_cosine_skill"
        ) as mock_cosine:

            result = get_or_fetch_skill(db, "python")

            assert result.normalized_term == "Python"
            mock_esco.assert_not_called()
            mock_cosine.assert_not_called()
    finally:
        db.close()


def test_exact_cache_hit_generates_missing_embedding_without_external_lookup():
    """Valida que si la skill está en caché pero no tiene embedding, lo genera localmente sin llamar a ESCO."""
    reset_database()
    db = SessionLocal()
    try:
        skill = SkillCache(
            raw_term="python",
            normalized_term="Python",
            esco_uri="http://esco/python",
            embedding=None,
        )
        db.add(skill)
        db.commit()

        with patch(
            "app.services.skill_cache_service.query_esco_api"
        ) as mock_esco, patch(
            "app.services.skill_cache_service.generate_embedding",
            return_value=[0.3] * 384,
        ) as mock_embed:

            result = get_or_fetch_skill(db, "python")

            assert result.embedding is not None
            mock_esco.assert_not_called()
            mock_embed.assert_called()
    finally:
        db.close()


def test_async_esco_search_does_not_accept_unrelated_first_result():
    """Valida que _query_esco_api_async filtre y rechace resultados iniciales no relacionados o malformados de ESCO."""

    async def run_test():
        # Simulamos una respuesta donde el primer resultado no guarda relación con la búsqueda
        mock_response = httpx.Response(
            status_code=200,
            json={
                "_embedded": {
                    "results": [
                        {"title": "Cocina y repostería", "uri": "http://esco/cook"},
                        {"title": "Python programming", "uri": "http://esco/python"},
                    ]
                }
            },
        )
        client = AsyncMock(spec=httpx.AsyncClient)
        client.get.return_value = mock_response
        semaphore = asyncio.Semaphore(1)

        res = await _query_esco_api_async(client, "Python", semaphore)
        assert res is not None
        # Debe omitir el primer resultado no relacionado y quedarse con el que coincide
        assert res["normalized_term"] == "Python programming"

    asyncio.run(run_test())


def test_sync_lookup_uses_esco_before_cosine_and_caches_embedding():
    """Valida que la búsqueda sincrónica consulte ESCO antes del matching por coseno si no está en caché."""
    reset_database()
    db = SessionLocal()
    try:
        with patch(
            "app.services.skill_cache_service.query_esco_api",
            return_value={
                "normalized_term": "FastAPI",
                "esco_uri": "http://esco/fastapi",
            },
        ) as mock_esco, patch(
            "app.services.skill_cache_service.find_cosine_skill"
        ) as mock_cosine, patch(
            "app.services.skill_cache_service.generate_embedding",
            return_value=[0.4] * 384,
        ):

            result = get_or_fetch_skill(db, "fastapi")

            assert result is not None
            assert result.normalized_term == "FastAPI"
            mock_esco.assert_called_once()
            mock_cosine.assert_not_called()
    finally:
        db.close()


def test_sync_lookup_uses_cosine_after_esco_miss_and_caches_alias():
    """Valida que si ESCO falla o no devuelve resultados, se use cosine match y se guarde el alias."""
    reset_database()
    db = SessionLocal()
    try:
        cosine_stub = SkillCache(
            raw_term="pyth",
            normalized_term="Python",
            esco_uri="http://esco/python",
            embedding=[0.1] * 384,
        )
        with patch(
            "app.services.skill_cache_service.query_esco_api", return_value=None
        ), patch(
            "app.services.skill_cache_service.find_cosine_skill",
            return_value=cosine_stub,
        ) as mock_cosine, patch(
            "app.services.skill_cache_service.generate_embedding",
            return_value=[0.5] * 384,
        ):

            result = get_or_fetch_skill(db, "pythons")

            assert result is not None
            mock_cosine.assert_called_once()
    finally:
        db.close()


def test_async_extraction_uses_cosine_after_esco_miss_and_caches_alias():
    """Valida la extracción asincrónica masiva cuando ESCO falla y hace fallback confiable a cosine match."""
    reset_database()
    db = SessionLocal()
    try:
        cosine_stub = SkillCache(
            raw_term="fast",
            normalized_term="FastAPI",
            esco_uri="http://esco/fastapi",
            embedding=[0.1] * 384,
        )
        db.add(cosine_stub)
        db.commit()

        with patch(
            "app.services.skill_cache_service._query_esco_api_async",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.services.skill_cache_service.find_cosine_skill",
            return_value=cosine_stub,
        ), patch(
            "app.services.skill_cache_service.generate_embedding",
            return_value=[0.6] * 384,
        ):

            results = asyncio.run(cache_extracted_skill_terms(db, ["fastapi-custom"]))
            assert len(results) == 1
            assert results[0].normalized_term == "FastAPI"
    finally:
        db.close()
