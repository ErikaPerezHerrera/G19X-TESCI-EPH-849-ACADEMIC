import asyncio

from google.genai.errors import ServerError

from app.api.v1.endpoints import resumes
from app.services import gemini_service


class FakeDatabase:
    def __init__(self):
        self.committed = False
        self.rolled_back = False

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


class FakeUpload:
    filename = "candidate.pdf"

    async def read(self):
        return b"pdf-bytes"


def test_pdf_extraction_enriches_anonymized_text_and_returns_enriched_fields(
    monkeypatch,
):
    extracted = {
        "full_name": "Ada Lovelace",
        "email": "ada@example.com",
        "phone": "1234567890",
        "raw_text": "Experiencia en [INFORMACIÓN_RESERVADA] con Python",
        "address": "Ciudad",
        "professional_title": "Perfil inicial",
        "technical_skills": ["Python"],
        "soft_skills": [],
        "work_experience": [],
        "extracted_skills": ["Python"],
        "parsed_data": {
            "full_name": "Ada Lovelace",
            "email": "ada@example.com",
            "phone": "1234567890",
            "professional_title": "Perfil inicial",
            "technical_skills": ["Python"],
            "soft_skills": [],
            "work_experience": [],
            "summary": "Resumen inicial",
            "more_info": "",
        },
    }
    enriched = {
        **extracted,
        "professional_title": "Desarrolladora backend",
        "technical_skills": ["Python", "FastAPI"],
        "parsed_data": {
            **extracted["parsed_data"],
            "professional_title": "Desarrolladora backend",
            "technical_skills": ["Python", "FastAPI"],
            "summary": "Desarrolladora backend con experiencia en APIs.",
        },
    }
    calls = []

    async def fake_extract_data(*_args, **_kwargs):
        return extracted

    def fake_enrich(raw_text, existing_data):
        calls.append((raw_text, existing_data))
        return {"data": enriched, "ai_available": True}

    monkeypatch.setattr(resumes, "extract_data_from_pdf", fake_extract_data)
    monkeypatch.setattr(resumes, "enrich_cv_extraction_with_status", fake_enrich)
    db = FakeDatabase()

    result = asyncio.run(resumes.extract_resume_file(FakeUpload(), db))

    assert calls == [(extracted["raw_text"], extracted)]
    assert result["professional_title"] == "Desarrolladora backend"
    assert result["technical_skills"] == ["Python", "FastAPI"]
    assert result["parsed_data"]["summary"] == (
        "Desarrolladora backend con experiencia en APIs."
    )
    assert result["email"] == "ada@example.com"
    assert result["ai_enrichment_status"] == "success"
    assert db.committed


def test_pdf_extraction_keeps_original_fields_when_ai_is_unavailable(monkeypatch):
    extracted = {
        "raw_text": "CV anonimizado",
        "technical_skills": ["Python"],
        "parsed_data": {"technical_skills": ["Python"]},
    }

    async def fake_extract_data(*_args, **_kwargs):
        return extracted

    def unavailable(*_args):
        return {"data": extracted, "ai_available": False}

    monkeypatch.setattr(resumes, "extract_data_from_pdf", fake_extract_data)
    monkeypatch.setattr(resumes, "enrich_cv_extraction_with_status", unavailable)

    result = asyncio.run(resumes.extract_resume_file(FakeUpload(), FakeDatabase()))

    assert result["technical_skills"] == ["Python"]
    assert result["ai_enrichment_status"] == "unavailable"


def test_cv_enrichment_preserves_identity_and_ignores_untrusted_response_fields(
    monkeypatch,
):
    existing = {
        "full_name": "Ada Lovelace",
        "email": "ada@example.com",
        "phone": "1234567890",
        "raw_text": "CV anonimizado",
        "professional_title": "Perfil inicial",
        "parsed_data": {
            "full_name": "Ada Lovelace",
            "email": "ada@example.com",
            "phone": "1234567890",
            "technical_skills": ["Python"],
        },
    }
    captured = {}

    def fake_generate(**kwargs):
        captured["prompt"] = kwargs["user_prompt"]
        return {
            "full_name": "Invented Name",
            "email": "invented@example.com",
            "phone": "9999999999",
            "raw_text": "replace original",
            "professional_title": "Ingeniera de software",
            "parsed_data": {
                "email_address": "invented@example.com",
                "technical_skills": ["Python", "FastAPI"],
            },
        }

    monkeypatch.setattr(gemini_service, "_generate_json_response", fake_generate)

    result = gemini_service.enrich_cv_extraction_with_status(
        "CV anonymized content",
        existing,
    )

    assert result["ai_available"] is True
    assert result["data"]["full_name"] == "Ada Lovelace"
    assert result["data"]["email"] == "ada@example.com"
    assert result["data"]["phone"] == "1234567890"
    assert result["data"]["raw_text"] == "CV anonimizado"
    assert result["data"]["professional_title"] == "Ingeniera de software"
    assert result["data"]["parsed_data"]["technical_skills"] == [
        "Python",
        "FastAPI",
    ]
    assert "ada@example.com" not in captured["prompt"]
    assert "Ada Lovelace" not in captured["prompt"]


def test_cv_enrichment_marks_empty_or_invalid_json_as_unavailable(monkeypatch):
    monkeypatch.setattr(
        gemini_service,
        "_generate_json_response",
        lambda **_kwargs: {"unexpected": "value"},
    )

    result = gemini_service.enrich_cv_extraction_with_status(
        "CV anonymized content",
        {"parsed_data": {"professional_title": "Perfil inicial"}},
    )

    assert result["ai_available"] is False
    assert result["data"]["parsed_data"]["professional_title"] == "Perfil inicial"


def test_gemini_request_retries_503_then_returns_success(monkeypatch):
    class FakeModels:
        def __init__(self):
            self.calls = 0

        def generate_content(self, **_kwargs):
            self.calls += 1
            if self.calls < 3:
                raise ServerError(503, {"message": "temporarily unavailable"})
            return type("Response", (), {"parsed": {"title": "Backend"}})()

    models = FakeModels()
    sleeps = []
    monkeypatch.setattr(
        gemini_service,
        "_get_client",
        lambda: type("Client", (), {"models": models})(),
    )
    monkeypatch.setattr(gemini_service.time, "sleep", sleeps.append)

    result = gemini_service._generate_json_response(
        system_prompt="system",
        user_prompt="user",
    )

    assert result == {"title": "Backend"}
    assert models.calls == 3
    assert sleeps == [1, 1]


def test_gemini_request_falls_back_after_exhausting_503_retries(monkeypatch):
    class FakeModels:
        def __init__(self):
            self.calls = 0

        def generate_content(self, **_kwargs):
            self.calls += 1
            raise ServerError(503, {"message": "temporarily unavailable"})

    models = FakeModels()
    sleeps = []
    monkeypatch.setattr(
        gemini_service,
        "_get_client",
        lambda: type("Client", (), {"models": models})(),
    )
    monkeypatch.setattr(gemini_service.time, "sleep", sleeps.append)

    result = gemini_service._generate_json_response(
        system_prompt="system",
        user_prompt="user",
    )

    assert result is None
    assert models.calls == 3
    assert sleeps == [1, 1]


def test_gemini_request_does_not_retry_other_http_errors(monkeypatch):
    class FakeModels:
        def __init__(self):
            self.calls = 0

        def generate_content(self, **_kwargs):
            self.calls += 1
            raise ServerError(500, {"message": "internal error"})

    models = FakeModels()
    sleeps = []
    monkeypatch.setattr(
        gemini_service,
        "_get_client",
        lambda: type("Client", (), {"models": models})(),
    )
    monkeypatch.setattr(gemini_service.time, "sleep", sleeps.append)

    result = gemini_service._generate_json_response(
        system_prompt="system",
        user_prompt="user",
    )

    assert result is None
    assert models.calls == 1
    assert sleeps == []
