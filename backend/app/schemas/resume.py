# Este código define la capa de Esquemas Pydantic para la gestión de Hojas de Vida / CVs (Resume).
# Es la estructura de datos responsable de recibir el texto procesado por los extractores/OCR
# y exponer la información estructurada por la IA (skills, datos parseados y referencias del archivo).

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

# ==========================================
# ESQUEMAS DE ENTRADA (SOLICITUDES / REQUESTS)
# ==========================================


class ResumeExtractRequest(BaseModel):
    """
    Entrada para los servicios o tareas que procesan texto crudo extraído de un PDF/Word.
    Valida que el contenido tenga un mínimo aceptable de caracteres para enviar a la IA.
    """

    raw_text: str = Field(
        ..., min_length=10, description="Texto completo extraído del documento PDF/Word"
    )


class ResumeCreate(BaseModel):
    """
    Estructura para persisitir un nuevo CV en la base de datos tras el parseo e inferencia.
    """

    candidate_email: EmailStr = Field(
        ..., description="Correo de contacto del candidato"
    )
    raw_text: str | None = Field(
        None, description="Texto crudo extraído del archivo original"
    )
    parsed_data: dict = Field(
        default_factory=dict,
        description="Estructura JSON con secciones de experiencia, educación, etc.",
    )
    extracted_skills: list[str] = Field(
        default_factory=list, description="Lista de habilidades/etiquetas identificadas"
    )
    file_name: str | None = Field(
        None, description="Nombre original del archivo adjuntado"
    )


# ==========================================
# ESQUEMAS DE RESPUESTA (RESPONSES)
# ==========================================


class ResumeOut(BaseModel):
    """
    Respuesta pública enviada al cliente o reclutador con el detalle estructurado del CV.
    Omitimos el campo 'embedding' (vector de 384 dimensiones) para reducir la carga de transferencia.
    """

    id: UUID
    user_id: UUID | None = None
    candidate_email: str
    raw_text: str | None = None
    parsed_data: dict
    extracted_skills: list[str]
    file_name: str | None = None

    class Config:
        # En Pydantic v2 mapea directamente los campos del objeto ORM de SQLAlchemy (db_resume)
        from_attributes = True
