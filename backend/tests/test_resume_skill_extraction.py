import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.services import skill_cache_service
from app.services.nlp_normalizer import extract_resume_skills
from app.services import pdf_extractor


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
        embedding=[0.1] * 384,
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
        patch.object(
            skill_cache_service, "generate_embedding", return_value=[0.1] * 384
        ),
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
        embedding=[0.2] * 384,
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


def test_async_esco_search_does_not_accept_unrelated_first_result():
    class Response:
        status_code = 200

        @staticmethod
        def json():
            return {
                "_embedded": {
                    "results": [{"title": "Administración de bases de datos"}]
                }
            }

    class Client:
        async def get(self, *_args, **_kwargs):
            return Response()

    result = asyncio.run(
        skill_cache_service._query_esco_api_async(
            Client(), "Kubernetes", asyncio.Semaphore(1)
        )
    )

    assert result is None


def test_exact_cache_hit_generates_missing_embedding_without_external_lookup():
    cached_record = SimpleNamespace(
        raw_term="Python",
        normalized_term="Python",
        embedding=None,
    )
    vector = [0.2] * 384
    db = SimpleNamespace(flush=lambda: None)

    with (
        patch.object(
            skill_cache_service, "find_exact_skill", return_value=cached_record
        ),
        patch.object(skill_cache_service, "generate_embedding", return_value=vector),
        patch.object(skill_cache_service, "query_esco_api") as esco_query,
        patch.object(skill_cache_service, "find_cosine_skill") as cosine_query,
    ):
        result = skill_cache_service.get_or_fetch_skill(db, "Python")

    assert result is cached_record
    assert cached_record.embedding == vector
    esco_query.assert_not_called()
    cosine_query.assert_not_called()


def test_sync_lookup_uses_esco_before_cosine_and_caches_embedding():
    record = SimpleNamespace(
        raw_term="Postgres",
        normalized_term="PostgreSQL",
        embedding=[0.3] * 384,
    )
    db = SimpleNamespace(query=lambda *_args: SimpleNamespace(
        filter=lambda *_conditions: SimpleNamespace(first=lambda: None)
    ))

    with (
        patch.object(skill_cache_service, "find_exact_skill", return_value=None),
        patch.object(
            skill_cache_service,
            "query_esco_api",
            return_value={
                "normalized_term": "PostgreSQL",
                "esco_uri": "esco:postgresql",
            },
        ),
        patch.object(skill_cache_service, "find_cosine_skill") as cosine_query,
        patch.object(
            skill_cache_service,
            "generate_embedding",
            return_value=record.embedding,
        ),
        patch.object(
            skill_cache_service, "_upsert_skill_record", return_value=record
        ) as upsert,
    ):
        result = skill_cache_service.get_or_fetch_skill(db, "Postgres")

    assert result is record
    cosine_query.assert_not_called()
    upsert.assert_called_once()
    assert upsert.call_args.kwargs["normalized_term"] == "PostgreSQL"
    assert upsert.call_args.kwargs["embedding"] == record.embedding


def test_sync_lookup_uses_cosine_after_esco_miss_and_caches_alias():
    canonical = SimpleNamespace(normalized_term="PostgreSQL")
    record = SimpleNamespace(
        raw_term="Postgres DB",
        normalized_term="PostgreSQL",
        embedding=[0.4] * 384,
    )
    db = SimpleNamespace(query=lambda *_args: SimpleNamespace(
        filter=lambda *_conditions: SimpleNamespace(first=lambda: None)
    ))

    with (
        patch.object(skill_cache_service, "find_exact_skill", return_value=None),
        patch.object(skill_cache_service, "query_esco_api", return_value=None),
        patch.object(
            skill_cache_service, "find_cosine_skill", return_value=canonical
        ) as cosine_query,
        patch.object(
            skill_cache_service,
            "generate_embedding",
            return_value=record.embedding,
        ),
        patch.object(
            skill_cache_service, "_upsert_skill_record", return_value=record
        ) as upsert,
    ):
        result = skill_cache_service.get_or_fetch_skill(db, "Postgres DB")

    assert result is record
    cosine_query.assert_called_once_with(db, "Postgres DB")
    assert upsert.call_args.kwargs["raw_term"] == "Postgres DB"
    assert upsert.call_args.kwargs["normalized_term"] == "PostgreSQL"
    assert upsert.call_args.kwargs["embedding"] == record.embedding


def test_async_extraction_uses_cosine_after_esco_miss_and_caches_alias():
    canonical = SimpleNamespace(normalized_term="PostgreSQL")
    record = SimpleNamespace(
        raw_term="Postgres DB",
        normalized_term="PostgreSQL",
        embedding=[0.5] * 384,
    )

    with (
        patch.object(skill_cache_service, "find_exact_skill", return_value=None),
        patch.object(
            skill_cache_service,
            "_query_esco_api_async",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch.object(
            skill_cache_service, "find_cosine_skill", return_value=canonical
        ) as cosine_query,
        patch.object(
            skill_cache_service,
            "generate_embedding",
            return_value=record.embedding,
        ),
        patch.object(
            skill_cache_service, "_upsert_skill_record", return_value=record
        ) as upsert,
    ):
        result = asyncio.run(
            skill_cache_service.cache_extracted_skill_terms(
                object(), ["Postgres DB"]
            )
        )

    assert result == [record]
    cosine_query.assert_called_once()
    assert upsert.call_args.kwargs["normalized_term"] == "PostgreSQL"
    assert upsert.call_args.kwargs["embedding"] == record.embedding


def test_backfill_generates_embeddings_for_existing_cache_rows():
    records = [
        SimpleNamespace(
            raw_term="Python",
            normalized_term="Python",
            embedding=None,
        ),
        SimpleNamespace(
            raw_term="Postgres",
            normalized_term="PostgreSQL",
            embedding=None,
        ),
    ]

    class Query:
        def filter(self, *_conditions):
            return self

        def order_by(self, *_columns):
            return self

        def all(self):
            return records

    db = SimpleNamespace(query=lambda *_models: Query(), flush=lambda: None)
    vector = [0.6] * 384

    with patch.object(
        skill_cache_service, "generate_embedding", return_value=vector
    ):
        updated = skill_cache_service.backfill_missing_skill_embeddings(db)

    assert updated == 2
    assert all(record.embedding == vector for record in records)


def test_pdf_extraction_caches_technical_and_soft_skills():
    db = object()
    with (
        patch.object(
            pdf_extractor,
            "convert_pdf_to_markdown",
            return_value="Resume contents",
        ),
        patch.object(
            pdf_extractor,
            "extract_resume_skills",
            return_value=(["Python"], ["Comunicación"]),
        ),
        patch.object(
            pdf_extractor,
            "cache_extracted_skill_terms",
            new_callable=AsyncMock,
        ) as cache_terms,
        patch.object(
            pdf_extractor, "clean_markdown_formatting", side_effect=lambda text: text
        ),
        patch.object(pdf_extractor, "extract_address_from_text", return_value=None),
        patch.object(
            pdf_extractor,
            "extract_name_and_anonymize",
            return_value=("Ada Lovelace", "Resume contents"),
        ),
        patch.object(
            pdf_extractor, "detect_student_or_academic_title", return_value=None
        ),
        patch.object(
            pdf_extractor, "extract_professional_title", return_value="Engineer"
        ),
        patch.object(
            pdf_extractor, "extract_work_experience_or_projects", return_value=[]
        ),
        patch.object(pdf_extractor, "extract_unclassified_info", return_value=""),
    ):
        result = asyncio.run(
            pdf_extractor.extract_data_from_pdf(b"pdf", "resume.pdf", db=db)
        )

    cache_terms.assert_awaited_once_with(db, ["Python", "Comunicación"])
    assert result["technical_skills"] == ["Python"]
    assert result["soft_skills"] == ["Comunicación"]
