# Este es el punto de entrada principal (main.py) de tu aplicación FastAPI en PluriJob.
# Se encarga de ensamblar las rutas, habilitar la integración CORS,
# verificar la disponibilidad de PostgreSQL e inicializar la extensión vectorial pgvector
# junto con las tablas del ORM.

import time

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine, get_db

# Se importan explícitamente todos los modelos ORM antes de invocar create_all()
# para garantizar que SQLAlchemy los registre en los metadatos globales.
from app.models.application import Application  # noqa: F401
from app.models.email_template import EmailTemplate  # noqa: F401
from app.models.job import Job  # noqa: F401
from app.models.resume import Resume  # noqa: F401
from app.models.skill_cache import SkillCache  # noqa: F401
from app.models.user import User  # noqa: F401
from app.services.skill_cache_service import backfill_missing_skill_embeddings

from app.api.v1.endpoints import applications

# Inicialización de la aplicación FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# Configuración del middleware de CORS (Cross-Origin Resource Sharing) para comunicación con el Frontend
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Inclusión de las rutas de la versión 1 de la API (/api/v1)
app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(auth_router, prefix=f"{settings.API_V1_STR}/auth")
app.include_router(applications.router, prefix="/api/v1", tags=["applications"])


def wait_for_database(max_retries: int = 20, delay_seconds: int = 2) -> None:
    """
    Realiza reintentos pasivos hasta que el contenedor/instancia de PostgreSQL esté listo.
    Evita fallos de arranque (race conditions) en entornos como Docker Compose.
    """
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
    """
    Evento de inicio de la aplicación:
    1. Espera la disponibilidad de la base de datos.
    2. Habilita la extensión pgvector ('CREATE EXTENSION IF NOT EXISTS vector').
    3. Crea las tablas de la base de datos según los modelos registrados en Base.metadata.
    4. Completa los embeddings faltantes de skills_cache.
    """
    try:
        wait_for_database()
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        Base.metadata.create_all(bind=engine)
        with engine.begin() as conn:
            conn.execute(
                text("ALTER TYPE job_status_enum ADD VALUE IF NOT EXISTS 'expired'")
            )
        with SessionLocal() as db:
            try:
                backfill_missing_skill_embeddings(db)
                db.commit()
            except Exception:
                db.rollback()
                raise
    except Exception as exc:
        raise RuntimeError(
            f"No se pudo inicializar PostgreSQL/pgvector: {exc}"
        ) from exc


@app.get("/")
def root():
    """Ruta raíz de bienvenida e indicación de documentación Swagger/OpenAPI."""
    return {"message": "Bienvenido a la API de PluriJob", "docs": "/docs"}


@app.get("/health", tags=["Health Check"])
def health_check(db: Session = Depends(get_db)):
    """
    Endpoint de diagnóstico para monitorear la salud del backend y verificar
    que la extensión pgvector esté instalada y habilitada correctamente.
    """
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
