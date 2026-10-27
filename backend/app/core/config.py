# backend/app/core/config.py
# Lectura de variables de entorno (.env)
# Este archivo lee el .env desde la carpeta backend y construye automáticamente la URL de conexión a PostgreSQL.
# Utiliza la librería Pydantic Settings para leer automáticamente las variables del archivo .env, validar que sus valores sean correctos y exponer los datos centralizados en el objeto settings.

import json
from pathlib import Path
from typing import Any, List, Optional
from urllib.parse import quote_plus

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """
    Clase de configuración principal basada en Pydantic.
    """

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- CONFIGURACIÓN GENERAL DEL PROYECTO ---
    PROJECT_NAME: str = "PluriJob API"
    API_V1_STR: str = "/api/v1"

    # --- CONFIGURACIÓN DE SEGURIDAD (JWT) ---
    # Sin valor por defecto: Pydantic exigirá que esté en el .env o variables de entorno
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # --- CONFIGURACIÓN DE BASE DE DATOS (PostgreSQL) ---
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    # ¡NUNCA dejes contraseñas reales aquí! Pon un valor vacío o elimina el default.
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str = "PluriJob"

    SQLALCHEMY_DATABASE_URI: Optional[str] = None

    @field_validator("SQLALCHEMY_DATABASE_URI", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Any, info) -> str:
        if isinstance(v, str) and v.strip():
            return v

        data = info.data
        user = quote_plus(str(data.get("POSTGRES_USER", "postgres")))
        password = quote_plus(str(data.get("POSTGRES_PASSWORD", "")))
        server = str(data.get("POSTGRES_SERVER", "localhost"))
        port = str(data.get("POSTGRES_PORT", 5432))
        db = str(data.get("POSTGRES_DB", "PluriJob"))

        if not server or not db:
            raise ValueError("POSTGRES_SERVER y POSTGRES_DB no pueden estar vacíos")

        return f"postgresql+psycopg2://{user}:{password}@{server}:{port}/{db}?sslmode=disable"

    ## Comentario: CONFIGURACION PARA ENVIAR CORREOS
    # (si SMTP_USER o SMTP_PASSWORD están vacíos, se simula) ---
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM_EMAIL: str = "noreply@plurijob.com"
    EMAILS_FROM_NAME: str = "PluriJob"

    # --- CONFIGURACIÓN DE CORS ---
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:3000",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    configured_origins = parsed
                else:
                    configured_origins = []
            except json.JSONDecodeError:
                configured_origins = [
                    origin.strip() for origin in v.split(",") if origin.strip()
                ]
        elif isinstance(v, list):
            configured_origins = v
        else:
            configured_origins = []

        required_local_origins = [
            "http://localhost:5500",
            "http://127.0.0.1:5500",
        ]
        return list(dict.fromkeys(required_local_origins + configured_origins))

    # --- INTEGRACIONES EXTERNAS ---
    # Si es obligatoria, déjala sin valor por defecto o pon Optional[str] = None si es opcional
    GEMINI_API_KEY: Optional[str] = None


settings = Settings()
