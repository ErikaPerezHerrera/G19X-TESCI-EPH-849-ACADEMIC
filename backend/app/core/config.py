# Lectura de variables de entorno (.env)
# Este archivo lee el .env desde la carpeta backend y construye automáticamente la URL de conexión a PostgreSQL.

import json
from pathlib import Path
from typing import Any, List, Optional
from urllib.parse import quote_plus

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    PROJECT_NAME: str = "PluriJob API"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "K1k@k0kA"
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

        return f"postgresql+psycopg2://{user}:{password}@{server}:{port}/{db}"

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
                    return parsed
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(",") if origin.strip()]
        if isinstance(v, list):
            return v
        return ["http://localhost:5500", "http://127.0.0.1:5500"]

    GEMINI_API_KEY: str = ""


settings = Settings()
