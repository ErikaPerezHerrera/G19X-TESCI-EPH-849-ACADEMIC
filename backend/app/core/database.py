# Conexión a PostgreSQL (SQLAlchemy + pgvector + retry)
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings


engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Fábrica de sesiones
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Clase base para los modelos
Base = declarative_base()


def get_db() -> Generator:
    """
    Inyección de dependencia de sesión de base de datos para FastAPI.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
