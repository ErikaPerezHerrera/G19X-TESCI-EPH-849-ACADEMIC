import os

# 1. Configurar variables de entorno para pruebas antes de importar la aplicación
os.environ["TESTING"] = "true"
TEST_DB_NAME = os.getenv("POSTGRES_DB_TEST", "plurijob_test")
os.environ["POSTGRES_DB"] = TEST_DB_NAME

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.config import settings
from app.core.database import get_db, Base,engine, SessionLocal
from app.core import database

# 2. Obtener o construir la URL de la base de datos de forma segura
# (Busca si existe DATABASE_URL, SQLALCHEMY_DATABASE_URI o la construye por partes)
base_url = getattr(settings, "DATABASE_URL", None) or getattr(
    settings, "SQLALCHEMY_DATABASE_URI", None
)

if base_url:
    # Si existe, solo reemplazamos el nombre de la base de datos por la de pruebas
    default_db = getattr(settings, "POSTGRES_DB", "plurijob")
    TEST_DATABASE_URL = str(base_url).replace(default_db, TEST_DB_NAME)
else:
    # Si no existe como atributo directo, la armamos con los datos individuales de settings o defaults
    db_user = getattr(settings, "POSTGRES_USER", "postgres")
    db_password = getattr(settings, "POSTGRES_PASSWORD", "postgres")
    db_server = getattr(settings, "POSTGRES_SERVER", "localhost")
    db_port = getattr(settings, "POSTGRES_PORT", "5432")
    TEST_DATABASE_URL = (
        f"postgresql://{db_user}:{db_password}@{db_server}:{db_port}/{TEST_DB_NAME}"
    )

# 3. Crear el motor (engine) de pruebas
engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Sobrescribir SessionLocal globalmente para que las funciones auxiliares usen la BD de prueba
database.SessionLocal = TestingSessionLocal


@pytest.fixture(autouse=True)
def setup_database():
    """Crea las tablas limpias antes de cada test y las elimina al finalizar."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """Cliente de pruebas de FastAPI con inyección de la sesión de prueba."""

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
