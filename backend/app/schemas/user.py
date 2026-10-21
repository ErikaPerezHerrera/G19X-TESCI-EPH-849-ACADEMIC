# Este módulo define la capa de Esquemas Pydantic para Autenticación y Usuarios (User) (app/schemas/user.py),

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

## Esquema de entrada (Input) para registrar un nuevo usuario en la plataforma
class UserCreate(BaseModel):
    """
    Datos requeridos para registrar un nuevo usuario en la plataforma PluriJob.
    Valida el formato del correo y que la contraseña cumpla con la longitud mínima de seguridad.
    """

    email: EmailStr = Field(..., description="Correo electrónico del usuario")
    password: str = Field(
        ..., min_length=6, description="Contraseña en texto plano (mínimo 6 caracteres)"
    )
    full_name: str | None = Field(
        None, description="Nombre completo del usuario (opcional)"
    )
    role: Literal["casual", "registered", "recruiter", "admin"] = Field(
        "casual",
        description="Rol del usuario en el sistema: 'casual', 'candidate' o 'recruiter'",
    )

## Esquema de entrada (Input) para el inicio de sesión de un usuario
class UserLogin(BaseModel):
    """
    Estructura de payload de entrada para el inicio de sesión (/login).
    """

    email: EmailStr = Field(..., description="Correo electrónico registrado")
    password: str = Field(..., description="Contraseña asociada a la cuenta")

## Esquema de salida (Output) para representar un usuario registrado
class UserOut(BaseModel):
    """
    Estructura pública de usuario enviada al cliente.
    Seguridad: Excluye explícitamente el campo 'password_hash' para evitar filtraciones de credenciales.
    """

    id: UUID
    email: EmailStr
    full_name: str | None = None
    role: Literal["casual", "registered", "recruiter", "admin"]
    is_active: bool = True

    class ConfigDict:
        # Pydantic v2: permite la conversión automática desde objetos ORM de SQLAlchemy (db_user)
        from_attributes = True

## Esquema de salida (Output) que devuelve el token JWT firmado y el rol tras un inicio de sesión exitoso
class Token(BaseModel):
    """
    Estructura de respuesta tras un inicio de sesión exitoso.
    Devuelve el Token JWT firmado para incluir en las futuras solicitudes HTTP Header Bearer.
    """

    access_token: str
    token_type: str = "bearer"
    email: EmailStr | None = None
    role: Literal["casual", "registered", "recruiter", "admin"] | None = None
