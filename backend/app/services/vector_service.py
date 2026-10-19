from typing import Optional

## Valores necesarios para manejar embeddings: dimensión, condición de creación, modelo
EMBEDDING_DIMENSION = 384
BGE_QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "
_EMBEDDING_MODEL = None

## Función para construir una consulta de creación de embedding
def build_query_embedding_text(text: Optional[str]) -> Optional[str]:
    content = (text or "").strip()
    if not content:
        return None
    return f"{BGE_QUERY_INSTRUCTION}{content}"

## Función para obtener el modelo del embedding y ver si fastembed está disponible
def _get_embedding_model():
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is None:
        try:
            from fastembed import TextEmbedding
        except ImportError as exc:
            raise RuntimeError(
                "fastembed no está disponible; no se pudo generar el embedding."
            ) from exc

        _EMBEDDING_MODEL = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")

    return _EMBEDDING_MODEL

## Función para generar el embedding de la descripción  de la vacante, dandole condición de creación
def generate_job_embedding(text: Optional[str]) -> Optional[list[float]]:
    return generate_embedding(text, instruction=BGE_QUERY_INSTRUCTION)

## Función para generar el embedding de la experiencia laborar, dandole condición de creación
def generate_resume_embedding(text: Optional[str]) -> Optional[list[float]]:
    return generate_embedding(text)

## Función principal para crear embeddings
def generate_embedding(
    text: Optional[str], instruction: Optional[str] = None
) -> Optional[list[float]]:
    content = (text or "").strip()
    if not content:
        return None

    if instruction:
        normalized_instruction = instruction.strip()
        if normalized_instruction and not content.startswith(normalized_instruction):
            content = f"{normalized_instruction}{content}"

    try:
        model = _get_embedding_model()
        vector = next(model.embed([content]), None)
        if vector is None:
            raise RuntimeError("El modelo no devolvió un vector para el texto.")

        values = vector.tolist() if hasattr(vector, "tolist") else list(vector)
        if len(values) != EMBEDDING_DIMENSION:
            raise RuntimeError(
                f"Dimensión de embedding inesperada: {len(values)}; "
                f"se requieren {EMBEDDING_DIMENSION}."
            )
        return [float(value) for value in values]
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"No se pudo generar el embedding.") from exc
