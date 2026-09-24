## Este es el módulo central de seguridad y autenticación de la aplicación.
# #Se encarga de tres cosas fundamentales:
# - encriptar y verificar contraseñas con bcrypt,
# - firmar y decodificar tokens JWT (JSON Web Tokens),
# - y proveer las dependencias que protegen tus rutas en FastAPI según el rol del usuario.
## Módulo central de seguridad y autenticación (PluriJob)
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


# --- 1. ENCRIPTACIÓN DE CONTRASEÑAS (Bcrypt Nativo) ---


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


# --- 2. GESTIÓN DE TOKENS JWT (PyJWT) ---


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


# --- 3. DEPENDENCIAS DE SEGURIDAD Y ROLES (FastAPI Guards) ---


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Extrae y valida el token JWT del Header Authorization Bearer.
    Retorna la instancia de User de PostgreSQL.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se proporcionaron credenciales de autenticación",
            headers={"WWW-Authenticate": "Bearer"},
        )

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

    # Si no lo encuentra por email, intenta buscar por UUID id (si decidieras usar ID como sub)
    if user is None:
        try:
            user = db.query(User).filter(User.id == identifier).first()
        except Exception:
            pass

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no válido o cuenta inactiva",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_current_recruiter(current_user: User = Depends(get_current_user)) -> User:
    """
    Guardia que restringe el acceso únicamente a usuarios con rol 'recruiter'.
    """
    if current_user.role != "recruiter":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren privilegios de reclutador para realizar esta acción",
        )
    return current_user


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
