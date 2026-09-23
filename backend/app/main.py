# Punto de entrada FastAPI
# Habilita CORS y valida que PostgreSQL + pgvector estén listos para recibir peticiones del frontend.

import time

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import engine, get_db

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def wait_for_database(max_retries: int = 20, delay_seconds: int = 2) -> None:
    for attempt in range(1, max_retries + 1):
        try:
            with engine.begin() as conn:
                conn.execute(text("SELECT 1"))
            return
        except Exception:
            if attempt == max_retries:
                raise
            time.sleep(delay_seconds)


@app.on_event("startup")
def startup_event() -> None:
    try:
        wait_for_database()
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
    except Exception as exc:
        raise RuntimeError(
            f"No se pudo inicializar PostgreSQL/pgvector: {exc}"
        ) from exc


@app.get("/")
def root():
    return {"message": "Bienvenido a la API de PluriJob", "docs": "/docs"}


@app.get("/health", tags=["Health Check"])
def health_check(db: Session = Depends(get_db)):
    """Verifica que la API y la extensión pgvector estén activas."""
    try:
        result = db.execute(
            text(
                "SELECT installed_version FROM pg_available_extensions WHERE name = 'vector';"
            )
        ).fetchone()

        if not result or not result[0]:
            raise HTTPException(
                status_code=500,
                detail="La extensión pgvector no está habilitada en PostgreSQL.",
            )

        return {
            "status": "online",
            "database": "connected",
            "pgvector_version": result[0],
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error de conexión a la base de datos: {str(exc)}",
        ) from exc
