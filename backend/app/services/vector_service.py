from typing import Optional

EMBEDDING_DIMENSION = 384
_EMBEDDING_MODEL = None


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


def generate_embedding(text: Optional[str]) -> Optional[list[float]]:
    content = (text or "").strip()
    if not content:
        return None

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
        raise RuntimeError(f"No se pudo generar el embedding: {exc}") from exc
