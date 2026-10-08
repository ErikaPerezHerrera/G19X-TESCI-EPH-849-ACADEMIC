# Este código define la capa de Esquemas Pydantic para la gestión de Ofertas Laborales (Job). 
# Permite validar los datos ingresados al momento de publicar una vacante y 
# dar formato a la respuesta que consume el cliente o el tablero del reclutador.

from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ==========================================
# ESQUEMAS DE ENTRADA (SOLICITUDES / REQUESTS)
# ==========================================


class JobCreate(BaseModel):
    """
    Datos requeridos y validaciones para que un reclutador pueda crear una nueva vacante.
    """

    title: str = Field(
        ..., min_length=3, description="Título del puesto (mínimo 3 caracteres)"
    )
    area: str = Field(
        ..., min_length=2, description="Área o departamento (ej: Tecnología)"
    )
    profile_type: str = Field(
        ...,
        min_length=2,
        description="Nivel o tipo de perfil (ej: Senior, Semi-Senior)",
    )
    modality: Literal["presencial", "remoto", "hibrido"] = Field(
        "presencial",
        description="Modalidad de trabajo: 'presencial', 'remoto' o 'híbrido'",
    )
    location: str | None = Field(
        None, description="Ubicación física de la oferta (opcional)"
    )
    description: str = Field(
        ...,
        min_length=10,
        description="Descripción detallada del puesto (mínimo 10 caracteres)",
    )
    technical_skills: List[str] = Field(
        default_factory=list, description="Lista de habilidades técnicas"
    )
    soft_skills: List[str] = Field(
        default_factory=list, description="Lista de habilidades blandas"
    )
    status: Literal["draft", "active", "closed", "expired"] = Field(
        "active",
        description="Estado inicial de la oferta: 'active', 'closed', 'expired'",
    )
    deadline: Optional[datetime] = Field(
        None, description="Fecha y hora límite de postulación"
    )
    benefits: Optional[str] = Field(None, description="Beneficios")


class JobReopen(BaseModel):
    """Campos admitidos al reabrir una vacante, validados según su estado actual."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(None, min_length=3)
    area: str | None = Field(None, min_length=2)
    profile_type: str | None = Field(None, min_length=2)
    modality: Literal["presencial", "remoto", "hibrido"] | None = None
    location: str | None = None
    description: str | None = Field(None, min_length=10)
    technical_skills: List[str] | None = None
    soft_skills: List[str] | None = None
    deadline: datetime | None = None
    benefits: str | None = None


# ==========================================
# ESQUEMAS DE RESPUESTA (RESPONSES)
# ==========================================


class JobOut(BaseModel):
    """
    Estructura pública de la oferta de trabajo devuelta por la API.
    Incluye identificadores únicos de la oferta y del reclutador propietario.
    """

    id: UUID
    recruiter_id: UUID
    title: str
    area: str
    profile_type: str
    modality: Literal["presencial", "remoto", "hibrido"]
    location: str | None = None
    description: str
    technical_skills: List[str]
    soft_skills: List[str]
    status: Literal["draft", "active", "closed", "expired"]
    deadline: Optional[datetime] = None
    benefits: Optional[str] = None

    class Config:
        # En Pydantic v2 mapea directamente las propiedades del objeto SQLAlchemy (db_job)
        from_attributes = True
