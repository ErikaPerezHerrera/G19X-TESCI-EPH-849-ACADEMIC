from types import SimpleNamespace

import pytest

from app.services import matching_engine
from app.services.matching_engine import calculate_match


@pytest.fixture(autouse=True)
def disable_external_gemini_requests(monkeypatch):
    monkeypatch.setattr(
        matching_engine,
        "analyze_candidate_compatibility",
        lambda *_args: {
            "status": "unavailable",
            "opinion": None,
            "pros": [],
            "cons": [],
            "overqualification_flag": "NO",
            "overqualification_reason": (
                "El análisis de IA no está configurado o no estuvo disponible; "
                "se completó el matching determinista."
            ),
        },
    )


def make_job(**overrides):
    values = {
        "technical_skills": ["Python", "PostgreSQL"],
        "embedding": [1.0] + [0.0] * 383,
        "profile_type": "Licenciatura en Sistemas",
        "description": "Desarrollo de APIs",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def make_resume(**overrides):
    values = {
        "parsed_data": {
            "technical_skills": ["python"],
            "professional_title": "Estudiante de Ingeniería en Sistemas",
            "work_experience": ["Construcción de APIs"],
        },
        "extracted_skills": ["python", "Comunicación"],
        "embedding": [1.0] + [0.0] * 383,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_score_combines_lexical_and_cosine_with_weights():
    result = calculate_match(make_job(), make_resume())

    assert result["match_score"] == 70.0
    assert result["match_details"]["exact_match"]["matched_skills"] == ["Python"]
    assert result["match_details"]["exact_match"]["missing_skills"] == ["PostgreSQL"]
    assert result["match_details"]["semantic_match"]["cosine_similarity"] == 1.0
    assert result["match_details"]["weights_used"]["exact_match_weight"] == 0.6
    assert result["match_details"]["weights_used"]["semantic_match_weight"] == 0.4
    assert result["match_details"]["overqualification"]["over_profile_type"] == "NO"
    assert "inputs" not in result["ai_analysis"]


def test_missing_embeddings_keep_lexical_score_and_mark_semantic_unavailable():
    result = calculate_match(
        make_job(embedding=None),
        make_resume(
            parsed_data={
                "technical_skills": ["Python", "PostgreSQL"],
                "professional_title": "Ingeniero en Sistemas",
            },
            embedding=None,
        ),
    )

    assert result["match_score"] == 60.0
    assert result["match_details"]["semantic_match"]["status"] == "unavailable"
    assert result["match_details"]["semantic_match"]["score"] is None


def test_low_exact_match_penalizes_semantic_similarity_by_30_percent():
    result = calculate_match(
        make_job(
            technical_skills=["Python", "PostgreSQL", "Docker"],
            embedding=[1.0] + [0.0] * 383,
        ),
        make_resume(
            parsed_data={
                "technical_skills": ["Java"],
                "professional_title": "Ingeniero en Sistemas",
            },
            embedding=[1.0] + [0.0] * 383,
        ),
    )

    assert result["match_details"]["exact_match"]["score"] == 0.0
    assert result["match_details"]["semantic_match"]["penalty_applied"] is True
    assert result["match_details"]["semantic_match"]["penalty_percentage"] == 0.3
    assert result["match_details"]["semantic_match"]["score"] == 0.7
    assert result["match_score"] == 28.0


def test_technical_overqualification_requires_match_and_five_extra_skills():
    result = calculate_match(
        make_job(technical_skills=["Python"]),
        make_resume(
            parsed_data={
                "technical_skills": [
                    "Python",
                    "Docker",
                    "Kubernetes",
                    "AWS",
                    "Terraform",
                    "Go",
                ],
                "professional_title": "Licenciado en Sistemas",
            }
        ),
    )

    overqualification = result["match_details"]["overqualification"]
    assert overqualification["over_technical_skills"] == "YES"
    assert result["is_overqualified"] is False


def test_higher_candidate_qualification_is_detected():
    result = calculate_match(
        make_job(profile_type="Licenciatura en Sistemas", embedding=None),
        make_resume(
            parsed_data={
                "technical_skills": ["Python"],
                "professional_title": "Maestría en Ciencias de la Computación",
            },
            embedding=None,
        ),
    )

    overqualification = result["match_details"]["overqualification"]
    assert overqualification["over_profile_type"] == "YES"
    assert overqualification["is_overqualified"] is False
    assert result["ai_analysis"]["status"] == "unavailable"
    assert overqualification["over_ia_analysis"] is None
    assert overqualification["over_technical_skills"] == "NO"


def test_two_positive_overqualification_signals_set_boolean():
    result = calculate_match(
        make_job(technical_skills=["Python"], profile_type="Licenciatura"),
        make_resume(
            parsed_data={
                "technical_skills": [
                    "Python",
                    "Docker",
                    "Kubernetes",
                    "AWS",
                    "Terraform",
                    "Go",
                ],
                "professional_title": "Maestría en Ciencias",
            }
        ),
    )

    assert result["is_overqualified"] is True
    assert result["match_details"]["overqualification"]["over_technical_skills"] == "YES"
    assert result["match_details"]["overqualification"]["over_profile_type"] == "YES"


def test_soft_skills_are_not_counted_as_extra_technical_skills():
    result = calculate_match(
        make_job(technical_skills=["Python"]),
        make_resume(
            parsed_data={
                "technical_skills": ["Python"],
                "soft_skills": ["Comunicación", "Liderazgo", "Empatía", "Organización", "Adaptabilidad"],
            },
            extracted_skills=[
                "Python",
                "Comunicación",
                "Liderazgo",
                "Empatía",
                "Organización",
                "Adaptabilidad",
            ],
        ),
    )

    assert result["match_details"]["exact_match"]["extra_skills"] == []
    assert result["match_details"]["overqualification"]["over_technical_skills"] == "NO"


def test_skill_cache_normalized_aliases_count_as_a_lexical_match():
    result = calculate_match(
        make_job(technical_skills=["PostgreSQL"], embedding=None),
        make_resume(
            parsed_data={
                "technical_skills": ["Postgres"],
                "professional_title": "Licenciado en Sistemas",
            },
            embedding=None,
        ),
        skill_aliases={"postgres": "postgresql"},
    )

    assert result["match_details"]["exact_match"]["score"] == 1.0
    assert result["match_details"]["exact_match"]["matched_skills"] == ["PostgreSQL"]


def test_ai_analysis_is_used_when_gemini_returns_success(monkeypatch):
    def fake_analyze(cv_data, job_data):
        return {
            "status": "success",
            "opinion": "Candidato con fuerte ajuste técnico.",
            "pros": ["Python", "APIs"],
            "cons": ["Falta liderazgo"],
            "overqualification_flag": "YES",
            "overqualification_reason": "Tiene experiencia superior al nivel requerido.",
        }

    monkeypatch.setattr(
        "app.services.matching_engine.analyze_candidate_compatibility",
        fake_analyze,
    )

    result = calculate_match(
        make_job(technical_skills=["Python"], profile_type="Licenciatura"),
        make_resume(
            parsed_data={
                "technical_skills": ["Python", "Docker", "Kubernetes"],
                "professional_title": "Maestría en Sistemas",
            }
        ),
    )

    assert result["ai_analysis"]["status"] == "success"
    assert result["ai_analysis"]["overqualification_flag"] == "YES"
    assert result["match_details"]["overqualification"]["over_ia_analysis"] == "YES"
    assert result["match_details"]["overqualification"]["over_technical_skills"] == "YES"
    assert result["match_details"]["overqualification"]["over_profile_type"] == "YES"
    assert result["match_details"]["overqualification"]["is_overqualified"] is True
    assert result["is_overqualified"] is True


def test_ai_overqualification_overrides_low_exact_match(monkeypatch):
    monkeypatch.setattr(
        matching_engine,
        "analyze_candidate_compatibility",
        lambda *_args: {
            "status": "success",
            "opinion": "La experiencia supera ampliamente lo requerido.",
            "pros": ["Experiencia avanzada"],
            "cons": [],
            "overqualification_flag": "YES",
            "overqualification_reason": "Experiencia superior al perfil requerido.",
        },
    )

    result = calculate_match(
        make_job(
            technical_skills=["Python", "PostgreSQL", "Docker"],
            profile_type="Junior",
            embedding=None,
        ),
        make_resume(
            parsed_data={
                "technical_skills": ["Java"],
                "professional_title": "Senior Architect",
            },
            embedding=None,
        ),
    )

    overqualification = result["match_details"]["overqualification"]
    assert result["match_details"]["exact_match"]["score"] == 0
    assert overqualification["over_ia_analysis"] == "YES"
    assert overqualification["over_technical_skills"] == "YES"
    assert overqualification["over_profile_type"] == "YES"
    assert overqualification["is_overqualified"] is True
    assert result["is_overqualified"] is True
