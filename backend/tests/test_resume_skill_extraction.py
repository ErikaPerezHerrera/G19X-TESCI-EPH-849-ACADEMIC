import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.services import skill_cache_service
from app.services.nlp_normalizer import extract_resume_skills


def test_extract_resume_skills_from_labeled_sections():
    text = (
        "HABILIDADES TÉCNICAS\n"
        "Python, PostgreSQL, FastAPI\n"
        "HABILIDADES BLANDAS\n"
        "Comunicación, trabajo en equipo\n"
        "EXPERIENCIA LABORAL\n"
        "Desarrolladora en una empresa"
    )

    assert extract_resume_skills(text) == (
        ["Python", "PostgreSQL", "FastAPI"],
        ["Comunicación", "trabajo en equipo"],
    )


def test_extract_resume_skills_from_generic_section_with_subcategories():
    text = (
        "## Habilidades\n"
        "Técnicas: Java, CI/CD\n"
        "Blandas: Adaptabilidad, Liderazgo\n"
        "Educación\n"
        "Ingeniería en Sistemas"
    )

    assert extract_resume_skills(text) == (
        ["Java", "CI/CD"],
        ["Adaptabilidad", "Liderazgo"],
    )


def test_cache_uses_esco_normalization_but_keeps_original_term():
    database_record = SimpleNamespace(
        raw_term="Postgres",
        normalized_term="PostgreSQL",
    )
    esco_data = {"normalized_term": "PostgreSQL", "esco_uri": "esco:postgresql"}

    with (
        patch.object(skill_cache_service, "find_exact_skill", return_value=None),
        patch.object(
            skill_cache_service,
            "_query_esco_api_async",
            new_callable=AsyncMock,
            return_value=esco_data,
        ),
        patch.object(skill_cache_service, "generate_embedding", return_value=None),
        patch.object(
            skill_cache_service, "_upsert_skill_record", return_value=database_record
        ) as upsert,
    ):
        result = asyncio.run(
            skill_cache_service.cache_extracted_skill_terms(object(), ["Postgres"])
        )

    assert result == [database_record]
    upsert.assert_called_once()
    assert upsert.call_args.kwargs["raw_term"] == "Postgres"
    assert upsert.call_args.kwargs["normalized_term"] == "PostgreSQL"


def test_cache_hit_does_not_query_esco():
    cached_record = SimpleNamespace(
        raw_term="Python",
        normalized_term="Python",
    )

    with (
        patch.object(
            skill_cache_service, "find_exact_skill", return_value=cached_record
        ),
        patch.object(
            skill_cache_service, "_query_esco_api_async", new_callable=AsyncMock
        ) as esco_query,
    ):
        result = asyncio.run(
            skill_cache_service.cache_extracted_skill_terms(object(), ["Python"])
        )

    assert result == [cached_record]
    esco_query.assert_not_awaited()
