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

from app.services.gemini_service import analyze_candidate_compatibility
from app.services.vector_service import EMBEDDING_DIMENSION

logger = logging.getLogger(__name__)

## Valores dados al motor de matching para calcular la coincidencia total y la sobrecalificación
EXACT_MATCH_WEIGHT = 0.60
SEMANTIC_MATCH_WEIGHT = 0.40
OVERQUALIFICATION_THRESHOLD = 0.90
MIN_EXTRA_SKILLS_FOR_OVERQUALIFICATION = 5

## Valores establecidos en caso de que la IA en gemini_service no esté configurada.
OVERQUALIFICATION_UNAVAILABLE_AI = {
    "status": "unavailable",
    "opinion": None,
    "overqualification_flag": None,
    "overqualification_reason": (
        "El análisis de IA no está configurado; se completó el matching determinista."
    ),
}

## Lista de valores que se buscan para establecer los niveles del Título académico y el Perfil buscado
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

## Función recursiva para convertir los datos que se le pasen en texto plano separando los elementos por saltos de línea.
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

## Función que procesa una lista completa de habilidades, las normaliza y las organiza en un diccionario (llama a la función _normalize_skill)
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

## Función que toma una habilidad en bruto y la transforma en una cadena de texto estándar y "limpia".
def _normalize_skill(skill: Any) -> str:
    if not isinstance(skill, str):
        return ""
    decomposed = unicodedata.normalize("NFKD", skill)
    unaccented = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    return re.sub(r"\s+", " ", unaccented).strip().casefold()

## Función que realiza la búsqueda por comparación de cosenos.
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

## Función que asigna el nivel del valor Proffesional_title. Se basa en la lista de valores _ACADEMIC_LEVELS (definida al principio del documento)
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

## Función que evalua sobrecalificación de acuerdo al nivel academico solicitado (perfil) y el nivel académico del candidato (título profesional)
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

## Función que intenta recuperar la información del análisis que hará la IA
def _fetch_ai_candidate_analysis(
    job: Job,
    resume: Resume,
) -> tuple[dict[str, Any], str, str | None]:
    parsed_data = resume.parsed_data or {}
    try:
        # Se intenta realizar el análisis y obtener un resultado en formato JSON
        analysis = analyze_candidate_compatibility(
            {
                "professional_title": parsed_data.get("professional_title"),
                "work_experience": parsed_data.get("work_experience") or [],
                "technical_skills": parsed_data.get("technical_skills") or [],
                "soft_skills": parsed_data.get("soft_skills") or [],
            },
            {
                "title": getattr(job, "title", ""),
                "profile_type": getattr(job, "profile_type", ""),
                "description": getattr(job, "description", ""),
                "technical_skills": getattr(job, "technical_skills", []) or [],
                "soft_skills": getattr(job, "soft_skills", []) or [],
            },
        )
    except Exception:
        ## En caso de que no se pueda ejecutar el análisis de IA,
        ## se regresan los valores establecidos para este caso. Se encuantran al inicio del documento
        logger.exception("No se pudo ejecutar el análisis cualitativo de IA del candidato.")
        return dict(OVERQUALIFICATION_UNAVAILABLE_AI), OVERQUALIFICATION_UNAVAILABLE_AI["overqualification_flag"], OVERQUALIFICATION_UNAVAILABLE_AI["overqualification_reason"]

    if not isinstance(analysis, dict):
        ## Si se hizo el análisis pero no regresó información, ## se regresan los valores establecidos para este caso. Se encuantran al inicio del documento
        return dict(OVERQUALIFICATION_UNAVAILABLE_AI), OVERQUALIFICATION_UNAVAILABLE_AI["overqualification_flag"], OVERQUALIFICATION_UNAVAILABLE_AI["overqualification_reason"]

    ## Si por alguna razon no se pudo hacer el análisis o conectar con Gemini, ## se regresan los valores establecidos para este caso. Se encuantran al inicio del documento
    status = str(analysis.get("status") or "unavailable").lower()
    if status != "success":
        return dict(OVERQUALIFICATION_UNAVAILABLE_AI), OVERQUALIFICATION_UNAVAILABLE_AI["overqualification_flag"], OVERQUALIFICATION_UNAVAILABLE_AI["overqualification_reason"]

    ## Si por la IA se consiguió una respuesta NO o no se obtuvo respuesta, el valor en ai_flag será NO
    ai_flag = str(analysis.get("overqualification_flag") or "NO").upper()
    if ai_flag not in {"YES", "NO"}:
        ai_flag = "NO"

    normalized = dict(OVERQUALIFICATION_UNAVAILABLE_AI)
    normalized.update(analysis)
    normalized["status"] = "success"
    normalized["overqualification_flag"] = ai_flag
    normalized["overqualification_reason"] = str(
        analysis.get("overqualification_reason")
        or OVERQUALIFICATION_UNAVAILABLE_AI["overqualification_reason"]
    ).strip() or OVERQUALIFICATION_UNAVAILABLE_AI["overqualification_reason"]
    return normalized, ai_flag, normalized["overqualification_reason"]

## Función para calcular el match
def calculate_match(
    job: Job,
    resume: Resume,
    skill_aliases: dict[str, str] | None = None,
) -> dict[str, Any]:
    """ Cálculo de match lexico y similitúd de cosenos entre CV y Vacante."""
    job_skills = _skills(job.technical_skills, skill_aliases)
    parsed_data = resume.parsed_data or {}
    candidate_skills = _skills(
        parsed_data.get("technical_skills"), skill_aliases
    )
    ## Calculo de coincidencia entre habilidades técnicas requeridas vs del candidato
    matched_keys = job_skills.keys() & candidate_skills.keys()
    missing_keys = job_skills.keys() - candidate_skills.keys()
    extra_keys = candidate_skills.keys() - job_skills.keys()
    ## Match léxico= habilidades que coinciden / habilidades solicitadas
    exact_score = (
        len(matched_keys) / len(job_skills)
        if job_skills
        else 1.0
    )

    ## Cálculo de similitud de cosenos entre Descripción del trabajo vs Experiencia Laboral
    semantic_score = _cosine_similarity(job.embedding, resume.embedding)

    ## Se aplica una penalización de 0.30 sobre el resultado de similitud de cosenos SI el match léxico es menor a 0.30
    semantic_penalty_applied = False
    semantic_penalty_percentage = 0.0
    if semantic_score is not None and exact_score < 0.30:
        semantic_penalty_applied = True
        semantic_penalty_percentage = 0.30
        semantic_score = semantic_score * 0.70
    ## El score general se calcula multiplicando los pesos de los scores por los scores obtenidos
    score = (
        EXACT_MATCH_WEIGHT * exact_score
        + SEMANTIC_MATCH_WEIGHT * (semantic_score or 0.0)
    )

    ## Se levanta la bandera de sobrecalificación si el match léxico es mayor a 0.95 y hay más de 5 habilidades no requeridas
    technical_overqualification = (
        "YES"
        if job_skills
        and exact_score > OVERQUALIFICATION_THRESHOLD
        and len(extra_keys) >= MIN_EXTRA_SKILLS_FOR_OVERQUALIFICATION
        else "NO"
    )

    ## Se llama a _profile_overqualification para saber si el nivel del candidato es mayor que el requerido
    profile_overqualification, profile_reason = _profile_overqualification(
        job.profile_type,
        parsed_data.get("professional_title"),
    )

    ## Se busca la información de análisis del candidato hecho por la IA.
    ## Si la IA hizo un análisis y determinó que el candidato está sobrecalificado, sobreescribe las banderas de
    ## sobrecalificación por habilidades y sobrecalificación por perfil.
    ai_analysis, ai_flag, ai_reason = _fetch_ai_candidate_analysis(job, resume)
    ai_analysis_available = ai_analysis.get("status") == "success"
    ai_overqualification_override = ai_analysis_available and ai_flag == "YES"
    if ai_overqualification_override:
        technical_overqualification = "YES"
        profile_overqualification = "YES"

    overqualification_flags = (
        technical_overqualification,
        profile_overqualification,
        ai_flag if ai_analysis_available else None,
    )

    ## Se requiere que haya 2 o más de 3 banderas por sobrecalificación con YES para calcular este booleano
    ## provocando que is_overqualified sea YES, desencadenando la visibilidad de ciertos datos (véase código en dashboard_recruiter.js)
    is_overqualified = (
        ai_analysis_available and ai_flag == "YES"
    ) or sum(flag == "YES" for flag in overqualification_flags) >= 2

    ## Prepara los resultados del análisis para guardar en la base de datos
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
                    "Se aplicó una penalización del 30% porque exact_match < 0.30."
                    if semantic_penalty_applied
                    else (
                        None
                        if semantic_score is not None
                        else "Falta un embedding válido para la vacante o el CV."
                    )
                ),
                "penalty_applied": semantic_penalty_applied,
                "penalty_percentage": semantic_penalty_percentage,
                "penalized_score": (
                    round(semantic_score, 4)
                    if semantic_score is not None
                    else None
                ),
            },
            "weights_used": {
                "exact_match_weight": EXACT_MATCH_WEIGHT,
                "semantic_match_weight": SEMANTIC_MATCH_WEIGHT,
                "score_formula": "0.60 * exact_match + 0.40 * semantic_match",
                "semantic_penalty_rule": (
                    "Si exact_match < 0.30, semantic_match se multiplica por 0.70."
                ),
            },
            "overqualification": {
                "over_technical_skills": technical_overqualification,
                "over_profile_type": profile_overqualification,
                "over_ia_analysis": ai_flag if ai_analysis_available else None,
                "is_overqualified": is_overqualified,
                "details": {
                    "technical_reason": (
                        f"Marcado por sobrecalificación positiva de IA: {ai_reason}"
                        if ai_overqualification_override
                        else (
                            f"{len(matched_keys)}/{len(job_skills)} habilidades "
                            f"requeridas coinciden y hay {len(extra_keys)} habilidades "
                            "técnicas adicionales."
                        )
                    ),
                    "profile_reason": (
                        f"Marcado por sobrecalificación positiva de IA: {ai_reason}"
                        if ai_overqualification_override
                        else profile_reason
                    ),
                    "ia_reason": ai_reason,
                },
            },
        },
        "ai_analysis": ai_analysis,
        "is_overqualified": is_overqualified,
    }

## Función que recopila las habilidades técnicas en Vacante y Cv, las normaliza, las busca en skills_cache y crea un diccionario con las habilidades encontradas para su consulta rápida
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

## Función principal para recalcular el matching y actualizar la postulación.
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

## Función que actualiza el matching al actualizar una vacante (por cambio de fecha y estatus de EXPIRED a ACIVE)
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

## Función que actualiza el matching al actualizar un CV (por aplicar una vacante o el usuario registrado guarda cambios del CV).
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
