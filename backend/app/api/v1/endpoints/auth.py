from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    get_current_admin,
    hash_password,
    verify_password,
)

from app.api.dependencies import get_current_user_dep

from app.models.resume import Resume
from app.models.user import User

from app.schemas.user import Token, UserCreate, UserLogin, UserOut

router = APIRouter(tags=["auth"])


## Determina el rol Admin o Registered según si ya existe un usuario con rol Admin en la base de datos.
def _resolve_registration_role(db: Session, requested_role: str | None) -> str:
    """El primer usuario registrado pasa a ser admin; el resto se registran como candidatas/os."""
    has_admin = db.query(User.id).filter(User.role == "admin").first() is not None
    if has_admin:
        return "registered"
    if requested_role == "admin":
        return "admin"
    return "admin"

## Ruta de autenticación y registro de usuarios
@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)

## Registro de usuario nuevo (rol registered o admin según corresponda)
def register_user(payload: UserCreate, db: Session = Depends(get_db)):
    """
    Registra un nuevo usuario en la plataforma.
    El primer usuario en resistrarse será admin; el resto se registran como candidatos.
    """
    email = payload.email.lower()
    if db.query(User).filter(func.lower(User.email) == email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo electrónico ya está registrado.",
        )

    resolved_role = _resolve_registration_role(db, payload.role)

    user = User(
        email=email,
        full_name=payload.full_name,
        role=resolved_role,
        password_hash=hash_password(payload.password),
        is_active=True,
    )
    # Se crea el usuario, y se asocia con un CV existente si corresponde y se cambia la fecha de expiración del CV a None para que no caduque.
    db.add(user)
    db.flush()
    resume = (
        db.query(Resume)
        .filter(
            func.lower(Resume.candidate_email) == email,
            or_(Resume.user_id.is_(None), Resume.user_id == user.id),
        )
        .first()
    )
    if resume is not None:
        resume.user_id = user.id
        resume.expires_at = None
    db.commit()
    db.refresh(user)
    return user

## Ruta administrativa para crear cuentas con rol recruiter
@router.post(
    "/register/recruiter",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
)
## Para poder crear la cuanta de recruiter, el usuario que hace la petición debe ser admin y estar autenticado.
def register_recruiter(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Ruta administrativa para crear cuentas con rol recruiter."""
    email = payload.email.lower()
    if db.query(User).filter(func.lower(User.email) == email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo electrónico ya está registrado.",
        )

    user = User(
        email=email,
        full_name=payload.full_name,
        role="recruiter",
        password_hash=hash_password(payload.password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

## Ruta de login para usuarios registrados
@router.post("/login", response_model=Token)
def login_user(payload: UserLogin, db: Session = Depends(get_db)):
    """
    Autentica al usuario contra PostgreSQL y genera un token JWT de acceso.
    """
    user = (
        db.query(User).filter(func.lower(User.email) == payload.email.lower()).first()
    )

    if (
        not user
        or not user.password_hash
        or not verify_password(payload.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo y/o contraseña incorrectos.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La cuenta de usuario está inactiva.",
        )

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.email,
        expires_delta=access_token_expires,
    )
    # Se devuelve el token de acceso junto con el correo electrónico y el rol del usuario.
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "email": user.email,
        "role": user.role,
    }


@router.get("/me", response_model=UserOut)
def read_current_user(current_user: User = Depends(get_current_user_dep)):
    """
    Retorna los datos del perfil del usuario actualmente autenticado mediante el JWT.
    """
    return current_user
