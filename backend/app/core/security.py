## Este es el módulo central de seguridad y autenticación de la aplicación.
# #Se encarga de tres cosas fundamentales:
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
# auto_error=False permite controlar el error manualmente si la petición no trae el token en el Header.
security_scheme = HTTPBearer(auto_error=False)


# --- 1. ENCRIPTACIÓN DE CONTRASENAS (Bcrypt) ---


def hash_password(password: str) -> str:
    """
    Recibe una contraseña en texto plano, genera una sal (salt) aleatoria
    y retorna la contraseña encriptada (hash) para guardarla de forma segura en la base de datos.
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """
    Compara una contraseña ingresada en texto plano con el hash guardado en la base de datos.
    Retorna True si coinciden, False de lo contrario.
    """
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


# --- 2. GESTIÓN DE TOKENS JWT (PyJWT) ---


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """
    Genera un token JWT firmado.
    - 'subject' (sub): Por lo general guarda el email o el ID del usuario.
    - Incluye marca de tiempo de creación ('iat') y fecha de expiración ('exp').
    """
    now = datetime.now(timezone.utc)
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": subject,
        "exp": now + expires_delta,
        "iat": now,
    }
    # Firma el token usando la clave secreta y el algoritmo (HS256) definidos en .env / config.py
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> str:
    """
    Decodifica y verifica la firma del token JWT.
    Si el token ha sido alterado, caducó o es inválido, lanza una excepción (ValueError).
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload["sub"]
    except jwt.PyJWTError as exc:
        raise ValueError("Token inválido") from exc


# --- 3. DEPENDENCIAS DE SEGURIDAD PARA RUTAS (FastAPI Guards) ---


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependencia que extrae el token del Header 'Authorization: Bearer <TOKEN>',
    lo valida, busca el usuario en PostgreSQL y confirma que esté activo.
    """
    # 1. Verifica si el cliente envió las credenciales HTTP
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autorizado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2. Decodifica el token para obtener el email
    try:
        email = decode_access_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    # 3. Busca el usuario en la base de datos
    user = db.query(User).filter(User.email == email).first()

    # 4. Verifica que el usuario exista y no esté desactivado
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no válido",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_current_recruiter(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependencia adicional para endpoints restringidos.
    Reutiliza 'get_current_user' y añade la validación de rol:
    Si el usuario no es 'recruiter', bloquea la petición devolviendo un HTTP 403 (Forbidden).
    """
    if current_user.role != "recruiter":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de reclutador",
        )
    return current_user
