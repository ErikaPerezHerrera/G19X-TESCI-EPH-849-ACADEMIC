# Lectura de variables de entorno (.env)
# Este archivo lee el .env desde la carpeta backend y construye automáticamente la URL de conexión a PostgreSQL.
# Este archivo es el corazón de la configuración del proyecto FastAPI. 
# Utiliza la librería Pydantic Settings para leer automáticamente las variables del archivo .env, validar que sus valores sean correctos y exponer los datos centralizados en el objeto settings.

import json
from pathlib import Path
from typing import Any, List, Optional
from urllib.parse import quote_plus

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Ubica la carpeta raíz del proyecto (navega 2 niveles hacia arriba desde este archivo)
# para encontrar la ruta absoluta del archivo .env
BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """
    Clase de configuración principal basada en Pydantic.
    Mapea automáticamente las variables de entorno del archivo .env a atributos de Python.
    """

    # Configuración de Pydantic para indicarle de dónde leer el archivo .env
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),  # Ruta al archivo .env
        env_file_encoding="utf-8",  # Codificación de texto
        case_sensitive=True,  # Distingue entre mayúsculas y minúsculas (ej: SECRET_KEY)
        extra="ignore",  # Ignora variables extra en el .env que no estén declaradas aquí
    )

    # --- CONFIGURACIÓN GENERAL DEL PROYECTO ---
    PROJECT_NAME: str = "PluriJob API"
    API_V1_STR: str = "/api/v1"

    # --- CONFIGURACIÓN DE SEGURIDAD (JWT) ---
    # Clave secreta para firmar los tokens JWT. Es OBLIGATORIA en el archivo .env
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # El token expira en 8 horas (480 min)

    # --- CONFIGURACIÓN DE BASE DE DATOS (PostgreSQL) ---
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "K1k@k0kA"
    POSTGRES_DB: str = "PluriJob"

    # URL completa que usará SQLAlchemy. Si no se pasa en el .env, se construye automáticamente
    SQLALCHEMY_DATABASE_URI: Optional[str] = None

    @field_validator("SQLALCHEMY_DATABASE_URI", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Any, info) -> str:
        """
        Validador que ensambla la URL de conexión de SQLAlchemy a partir de las credenciales.
        Usa 'quote_plus' para codificar caracteres especiales en la contraseña (como '@', '#', etc.)
        evitando que rompan la URL.
        """
        # Si ya se definió manualmente la URL completa en el .env, la respeta
        if isinstance(v, str) and v.strip():
            return v

        # Extrae los valores individuales
        data = info.data
        user = quote_plus(str(data.get("POSTGRES_USER", "postgres")))
        password = quote_plus(str(data.get("POSTGRES_PASSWORD", "")))
        server = str(data.get("POSTGRES_SERVER", "localhost"))
        port = str(data.get("POSTGRES_PORT", 5432))
        db = str(data.get("POSTGRES_DB", "PluriJob"))

        if not server or not db:
            raise ValueError("POSTGRES_SERVER y POSTGRES_DB no pueden estar vacíos")

        # Construye la URL final con el conector psycopg2
        return f"postgresql+psycopg2://{user}:{password}@{server}:{port}/{db}"

    # --- CONFIGURACIÓN DE CORS (Política de Orígenes Cruzados) ---
    # Define qué páginas/orígenes frontend tienen permiso para consumir esta API
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:3000",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> List[str]:
        """
        Validador para permitir que BACKEND_CORS_ORIGINS en el .env
        se escriba como lista JSON '["http://..."]' o separada por comas 'http://...,http://...'
        """
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                # Si no es un JSON válido, divide por comas
                return [origin.strip() for origin in v.split(",") if origin.strip()]
        if isinstance(v, list):
            return v
        return ["http://localhost:5500", "http://127.0.0.1:5500"]

    # --- INTEGRACIONES EXTERNAS ---
    GEMINI_API_KEY: str = ""  # Clave de la API de Google Gemini (opcional en MVP)


# Instancia única (Singleton) que importarás en todo el proyecto:
# ej: from app.core.config import settings
settings = Settings()
