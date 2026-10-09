import logging
import math
import re
import unicodedata
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.application import Application
from app.models.job import Job
from app.models.resume import Resume
from app.models.skill_cache import SkillCache
from app.services.vector_service import EMBEDDING_DIMENSION

logger = logging.getLogger(__name__)

EXACT_MATCH_WEIGHT = 0.60
SEMANTIC_MATCH_WEIGHT = 0.40
OVERQUALIFICATION_THRESHOLD = 0.95
MIN_EXTRA_SKILLS_FOR_OVERQUALIFICATION = 5

OVERQUALIFICATION_UNAVAILABLE_AI = {
    "status": "unavailable",
    "opinion": None,
    "overqualification_flag": None,
    "overqualification_reason": (
        "El análisis de IA no está configurado; se completó el matching determinista."
    ),
}

_ACADEMIC_LEVELS = (
    (
        6,
        re.compile(
            r"\b(?:doctorado|doctoral|doctor|phd|ph\.d|dphil)\b",
            re.IGNORECASE,
        ),
    ),
    (
        5,
        re.compile(
            r"\b(?:maestria|maestro|maestra|master|magister|mba)\b",
            re.IGNORECASE,
        ),
    ),
    (
        4,
        re.compile(
            r"\b(?:especialidad|especialista|posgrado|postgrado|postgraduate)\b",
            re.IGNORECASE,
        ),
    ),
    (
        3,
        re.compile(
            r"\b(?:licenciatura|licenciado|licenciada|ingenieria|ingeniero|"
            r"ingeniera|bachelor|undergraduate|grado universitario)\b",
            re.IGNORECASE,
        ),
    ),
    (
        2,
        re.compile(
            r"\b(?:junior|jr|pasante|practicante|intern|becario|trainee)\b",
            re.IGNORECASE,
        ),
    ),
    (
        1,
        re.compile(
            r"\b(?:estudiante|student|en curso|cursando)\b",
            re.IGNORECASE,
        ),
    ),
)


def _plain_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(
            text for item in value if (text := _plain_text(item)).strip()
        )
    if isinstance(value, dict):
        return "\n".join(
            text for item in value.values() if (text := _plain_text(item)).strip()
        )
    return ""


def _normalize_skill(skill: Any) -> str:
    if not isinstance(skill, str):
        return ""
    decomposed = unicodedata.normalize("NFKD", skill)
    unaccented = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    return re.sub(r"\s+", " ", unaccented).strip().casefold()


def _skills(
    values: Any, skill_aliases: dict[str, str] | None = None
) -> dict[str, str]:
    if not isinstance(values, list):
        return {}
    result: dict[str, str] = {}
    for value in values:
        normalized = _normalize_skill(value)
        if normalized:
            result.setdefault(
                (skill_aliases or {}).get(normalized, normalized), value.strip()
            )
    return result


def _embedding_values(embedding: Any) -> list[float] | None:
    try:
        values = [float(value) for value in embedding]
    except (TypeError, ValueError):
        return None
    return values if len(values) == EMBEDDING_DIMENSION else None


def _cosine_similarity(left: Any, right: Any) -> float | None:
    try:
        left_values = [float(value) for value in left]
        right_values = [float(value) for value in right]
    except (TypeError, ValueError):
        return None

    if (
        len(left_values) != EMBEDDING_DIMENSION
        or len(right_values) != EMBEDDING_DIMENSION
    ):
        return None

    left_norm = math.sqrt(sum(value * value for value in left_values))
    right_norm = math.sqrt(sum(value * value for value in right_values))
    if left_norm == 0 or right_norm == 0:
        return None

    cosine = sum(a * b for a, b in zip(left_values, right_values)) / (
        left_norm * right_norm
    )
    return max(0.0, min(1.0, cosine))


def _academic_level(text: str, *, candidate: bool = False) -> int | None:
    normalized_text = _normalize_skill(text)
    if candidate and re.search(
        r"\b(?:estudiante|student|en curso|cursando)\b",
        normalized_text,
        re.IGNORECASE,
    ):
        return 1

    levels = [
        level
        for level, pattern in _ACADEMIC_LEVELS
        if pattern.search(normalized_text)
    ]
    return max(levels) if levels else None


def _profile_overqualification(
    profile_type: Any, professional_title: Any
) -> tuple[str, str]:
    required_text = _plain_text(profile_type)
    candidate_text = _plain_text(professional_title)
    required_level = _academic_level(required_text)
    candidate_level = _academic_level(candidate_text, candidate=True)

    if required_level is None or candidate_level is None:
        return (
            "NO",
            "No se identificó un nivel académico comparable en ambos perfiles.",
        )
    if candidate_level > required_level:
        return (
            "YES",
            f"El nivel académico detectado en el CV ({candidate_level}) supera "
            f"el nivel indicado por la vacante ({required_level}).",
        )
    return (
        "NO",
        f"El nivel académico del CV ({candidate_level}) no supera el requerido "
        f"por la vacante ({required_level}).",
    )


def calculate_match(
    job: Job,
    resume: Resume,
    skill_aliases: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Calculate explainable lexical and cosine match values for a job and CV."""
    job_skills = _skills(job.technical_skills, skill_aliases)
    parsed_data = resume.parsed_data or {}
    candidate_skills = _skills(
        parsed_data.get("technical_skills"), skill_aliases
    )

    matched_keys = job_skills.keys() & candidate_skills.keys()
    missing_keys = job_skills.keys() - candidate_skills.keys()
    extra_keys = candidate_skills.keys() - job_skills.keys()
    exact_score = (
        len(matched_keys) / len(job_skills)
        if job_skills
        else 1.0
    )

    semantic_score = _cosine_similarity(job.embedding, resume.embedding)
    score = (
        EXACT_MATCH_WEIGHT * exact_score
        + SEMANTIC_MATCH_WEIGHT * (semantic_score or 0.0)
    )

    technical_overqualification = (
        "YES"
        if job_skills
        and exact_score > OVERQUALIFICATION_THRESHOLD
        and len(extra_keys) >= MIN_EXTRA_SKILLS_FOR_OVERQUALIFICATION
        else "NO"
    )
    profile_overqualification, profile_reason = _profile_overqualification(
        job.profile_type,
        parsed_data.get("professional_title"),
    )
    ai_flag = OVERQUALIFICATION_UNAVAILABLE_AI["overqualification_flag"]
    overqualification_flags = (
        technical_overqualification,
        profile_overqualification,
        ai_flag,
    )
    is_overqualified = sum(flag == "YES" for flag in overqualification_flags) >= 2

    ai_analysis = dict(OVERQUALIFICATION_UNAVAILABLE_AI)
    ai_analysis["inputs"] = {
        "technical_skills": {
            "job": list(job_skills.values()),
            "candidate": list(candidate_skills.values()),
        },
        "job_description": job.description,
        "experience": _plain_text(parsed_data.get("work_experience")),
        "job_embedding": _embedding_values(job.embedding),
        "resume_embedding": _embedding_values(resume.embedding),
    }

    return {
        "match_score": round(score * 100, 2),
        "match_details": {
            "exact_match": {
                "score": round(exact_score, 4),
                "matched_skills": [job_skills[key] for key in sorted(matched_keys)],
                "missing_skills": [job_skills[key] for key in sorted(missing_keys)],
                "extra_skills": [
                    candidate_skills[key] for key in sorted(extra_keys)
                ],
                "total_required": len(job_skills),
            },
            "semantic_match": {
                "score": (
                    round(semantic_score, 4)
                    if semantic_score is not None
                    else None
                ),
                "cosine_similarity": (
                    round(semantic_score, 4)
                    if semantic_score is not None
                    else None
                ),
                "status": (
                    "available" if semantic_score is not None else "unavailable"
                ),
                "reason": (
                    None
                    if semantic_score is not None
                    else "Falta un embedding válido para la vacante o el CV."
                ),
            },
            "weights_used": {
                "exact_match_weight": EXACT_MATCH_WEIGHT,
                "semantic_match_weight": SEMANTIC_MATCH_WEIGHT,
                "score_formula": "0.60 * exact_match + 0.40 * semantic_match",
            },
            "overqualification": {
                "over_technical_skills": technical_overqualification,
                "over_profile_type": profile_overqualification,
                "over_ia_analysis": None,
                "is_overqualified": is_overqualified,
                "details": {
                    "technical_reason": (
                        f"{len(matched_keys)}/{len(job_skills)} habilidades "
                        f"requeridas coinciden y hay {len(extra_keys)} habilidades "
                        "técnicas adicionales."
                    ),
                    "profile_reason": profile_reason,
                    "ia_reason": OVERQUALIFICATION_UNAVAILABLE_AI[
                        "overqualification_reason"
                    ],
                },
            },
        },
        "ai_analysis": ai_analysis,
        "is_overqualified": is_overqualified,
    }


def _load_skill_aliases(
    db: Session, job: Job, resume: Resume
) -> dict[str, str]:
    parsed_data = resume.parsed_data or {}
    terms: list[str] = []
    for skill_list in (
        job.technical_skills,
        parsed_data.get("technical_skills"),
    ):
        if isinstance(skill_list, list):
            terms.extend(
                term for term in skill_list if isinstance(term, str) and term.strip()
            )
    raw_terms = {term.strip().casefold() for term in terms}
    if not raw_terms:
        return {}

    records = (
        db.query(SkillCache)
        .filter(func.lower(SkillCache.raw_term).in_(raw_terms))
        .all()
    )
    return {
        _normalize_skill(record.raw_term): _normalize_skill(record.normalized_term)
        for record in records
        if record.normalized_term
    }


def recalculate_application_match(
    application: Application, db: Session | None = None
) -> Application:
    job = application.job
    resume = application.resume
    if job is None or resume is None:
        raise ValueError(
            f"La postulación {application.id} no tiene vacante o CV asociado."
        )

    skill_aliases = _load_skill_aliases(db, job, resume) if db is not None else None
    result = calculate_match(job, resume, skill_aliases)
    application.match_score = result["match_score"]
    application.match_details = result["match_details"]
    application.ai_analysis = result["ai_analysis"]
    application.is_overqualified = result["is_overqualified"]
    return application


def recalculate_job_applications(db: Session, job_id: Any) -> int:
    applications = (
        db.query(Application)
        .options(joinedload(Application.job), joinedload(Application.resume))
        .filter(Application.job_id == job_id)
        .all()
    )
    for application in applications:
        recalculate_application_match(application, db)
    if applications:
        db.commit()
    return len(applications)


def recalculate_resume_applications(db: Session, resume_id: Any) -> int:
    applications = (
        db.query(Application)
        .options(joinedload(Application.job), joinedload(Application.resume))
        .filter(Application.resume_id == resume_id)
        .all()
    )
    for application in applications:
        recalculate_application_match(application, db)
    if applications:
        db.commit()
    return len(applications)
