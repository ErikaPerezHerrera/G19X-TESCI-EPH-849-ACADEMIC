from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
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
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserLogin, UserOut

router = APIRouter(tags=["auth"])


def _resolve_registration_role(db: Session, requested_role: str | None) -> str:
    """El primer usuario registrado pasa a ser admin; el resto se registran como candidatas/os."""
    has_admin = db.query(User.id).filter(User.role == "admin").first() is not None
    if has_admin:
        return "registered"
    if requested_role == "admin":
        return "admin"
    return "admin"


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register_user(payload: UserCreate, db: Session = Depends(get_db)):
    """
    Registra un nuevo usuario en la plataforma.
    El primer usuario sin administrador será admin; el resto se registran como candidatos.
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
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post(
    "/register/recruiter",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
)
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
            detail="No estás registrado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La cuenta de usuario está inactiva.",
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.email,
        expires_delta=access_token_expires,
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserOut)
def read_current_user(current_user: User = Depends(get_current_user_dep)):
    """
    Retorna los datos del perfil del usuario actualmente autenticado mediante el JWT.
    """
    return current_user
