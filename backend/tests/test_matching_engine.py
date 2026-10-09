from types import SimpleNamespace

from app.services.matching_engine import calculate_match


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
