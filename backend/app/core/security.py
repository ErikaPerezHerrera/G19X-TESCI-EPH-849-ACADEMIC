## Módulo central de seguridad y autenticación (PluriJob)
# Se encarga de tres cosas fundamentales:
# - encriptar y verificar contraseñas con bcrypt,
# - firmar y decodificar tokens JWT (JSON Web Tokens),
# - y proveer las dependencias que protegen tus rutas en FastAPI según el rol del usuario.

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db

from app.models.user import User

# Esquema de autenticación Bearer Token de FastAPI.
security_scheme = HTTPBearer(auto_error=False)

## Gestión de contraseñas y tokens
def hash_password(password: str) -> str:
    """
    Genera un hash seguro utilizando bcrypt directamente.
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """
    Compara la contraseña ingresada en texto plano contra el hash de la DB.
    """
    if not password_hash:
        return False
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


## Gestión de tokens JWT
def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """
    Genera un token JWT firmado mediante HS256.
    """
    now = datetime.now(timezone.utc)
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": str(subject),
        "exp": now + expires_delta,
        "iat": now,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> str:
    """
    Decodifica y verifica el token JWT. Retorna el 'sub' (email o ID).
    Lanza ValueError si el token expiró o es inválido.
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        sub: str | None = payload.get("sub")
        if not sub:
            raise ValueError("Payload sin campo sub")
        return sub
    except jwt.PyJWTError as exc:
        raise ValueError("Token inválido o expirado") from exc


## Busqueda de usuario actual registrado o establece una visita anónima
def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    """
    Devuelve el usuario autenticado cuando se envía un token, o None para visitas anónimas.
    """
    if credentials is None:
        return None

    try:
        identifier = decode_access_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acceso inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    # Busca por email
    user = db.query(User).filter(User.email == identifier).first()

    # Si no lo encuentra por email, intenta buscar por UUID id
    if user is None:
        try:
            user = db.query(User).filter(User.id == identifier).first()
        except Exception:
            pass
    # Si el usuario no es encontrado o no está activo lanza un error de acceso no autorizado
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no válido o cuenta inactiva",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user

## Revisión de permiso de acceso autenticado
def get_current_user(
    current_user: User | None = Depends(get_optional_current_user),
) -> User:
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se proporcionaron credenciales de autenticación",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user

## Guardia de acceso para rol Administrador
def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Guardia que restringe el acceso únicamente a administradores.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren privilegios de administrador para realizar esta acción",
        )
    return current_user

## Guardia de acceso para rol Reclutador
def get_current_recruiter(current_user: User = Depends(get_current_user)) -> User:
    """
    Guardia que permite acceso a reclutadores y administradores.
    """
    if current_user.role not in ("recruiter", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren privilegios de reclutador o administrador para realizar esta acción",
        )
    return current_user

## Guardia de acceso para rol Registrado o Casual
def get_current_candidate(current_user: User = Depends(get_current_user)) -> User:
    """
    Guardia que restringe el acceso a usuarios postulantes ('registered' o 'casual').
    """
    if current_user.role not in ["registered", "casual"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Este recurso es exclusivo para candidatos",
        )
    return current_user