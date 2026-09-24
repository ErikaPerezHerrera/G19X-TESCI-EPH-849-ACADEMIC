# Este archivo define la capa de Esquemas Pydantic para las Postulaciones (Application).
# Se encarga de validar los datos recibidos al crear una postulación y
# de estructurar la respuesta enviada al cliente, incluyendo el desglose de matching y el análisis de la IA.
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

# ==========================================
# ESQUEMAS DE ENTRADA (SOLICITUDES / REQUESTS)
# ==========================================


class ApplicationCreate(BaseModel):
    """
    Datos requeridos para crear una nueva postulación a una vacante.
    Maneja tanto a usuarios registrados (user_id) como a candidatos casuales/anónimos.
    """

    resume_id: UUID = Field(
        ..., description="ID del currículum que se utilizará para la postulación"
    )
    candidate_email: EmailStr = Field(
        ..., description="Correo de contacto del candidato"
    )
    user_id: UUID | None = Field(
        None,
        description="ID del usuario registrado (opcional si es un candidato casual)",
    )
    match_score: float | None = Field(
        None,
        ge=0,
        le=100,
        description="Puntuación inicial calculada antes de persistir",
    )


# ==========================================
# ESQUEMAS DE RESPUESTA (RESPONSES)
# ==========================================


class ApplicationOut(BaseModel):
    """
    Estructura completa de la postulación entregada al cliente o reclutador.
    Incluye la auditoría de matching (match_details) y el análisis de sobrecalificación.
    """

    id: UUID
    job_id: UUID
    user_id: UUID | None = None
    resume_id: UUID
    candidate_email: str
    status: Literal[
        "received",
        "under_review",
        "shortlisted",
        "interview_scheduled",
        "rejected",
        "hired",
    ]
    match_score: float | None = Field(None, ge=0, le=100)
    is_overqualified: bool = False
    ai_analysis: dict = Field(
        default_factory=dict,
        description="Comentarios u observaciones generadas por la IA",
    )
    match_details: dict = Field(
        default_factory=dict,
        description="Desglose explicativo de la puntuación (skills, vectores)",
    )
    rejection_reason: str | None = None

    class Config:
        # En Pydantic v2 permite mapear directamente desde el objeto ORM de SQLAlchemy (db_application)
        from_attributes = True
