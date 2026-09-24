# Conexión a PostgreSQL (SQLAlchemy + pgvector)
# Es el archivo encargado de gestionar la conexión física con PostgreSQL, administrar el pool de conexiones y proveer la sesión de base de datos a cada petición en FastAPI.

from typing import Generator

from pgvector.sqlalchemy import Vector
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

# 1. MOTOR DE BASE DE DATOS (Engine)
# Es el punto de entrada que administra el pool de conexiones con PostgreSQL usando la URI de config.py.
engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    # Verificación de conexión (Health Check):
    # Antes de entregar una conexión del pool, prueba que siga viva. Si PostgreSQL se reinició, la reconecta automáticamente.
    pool_pre_ping=True,
    # Conexiones base del pool que se mantienen abiertas en memoria:
    pool_size=10,
    # Conexiones adicionales permitidas durante picos de tráfico (10 base + 20 extra = hasta 30 conexiones simultáneas):
    max_overflow=20,
)

# 2. FÁBRICA DE SESIONES (SessionLocal)
# Generador de sesiones individuales para hacer consultas (SELECT, INSERT, UPDATE, DELETE).
# autocommit=False -> Exige hacer `db.commit()` explícito para guardar cambios (evita guardar errores por accidente).
# autoflush=False -> Evita emitir SQL a la base de datos automáticamente antes de cada consulta hasta que se pida explícitamente.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 3. CLASE BASE PARA LOS MODELOS (DeclarativeBase)
# Todos los modelos de la base de datos (User, Job, Resume, Application) heredan de esta clase `Base`.
Base = declarative_base()


# 4. DEPENDENCIA DE INYECCIÓN PARA FASTAPI (get_db)
# Gestiona el ciclo de vida de la sesión en cada request HTTP.
def get_db() -> Generator:
    """
    Abre una sesión de base de datos al recibir una solicitud en FastAPI
    y se asegura de cerrarla SIEMPRE al terminar, incluso si ocurre un error.
    """
    db = SessionLocal()  # Abre la sesión
    try:
        yield db  # Entrega la sesión al endpoint que la solicitó
    finally:
        db.close()  # Cierra la sesión y regresa la conexión al pool de SQLAlchemy
