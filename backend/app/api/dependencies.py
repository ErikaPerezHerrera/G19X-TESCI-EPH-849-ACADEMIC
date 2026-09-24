## Estas funciones actúan como "guardianes" (middlewares/guards) en las rutas de FastAPI.
## Cuando pasan como parámetros dentro de Depends(...), FastAPI ejecuta toda la cadena de validación antes de correr el código del endpoint

from fastapi import Depends

from app.core.security import (
    get_current_candidate as _get_current_candidate,
    get_current_recruiter as _get_current_recruiter,
    get_current_user as _get_current_user,
)
from app.models.user import User


def get_current_user_dep(
    user: User = Depends(_get_current_user),
) -> User:
    """
    Protege rutas que requieren cualquier usuario autenticado
    (casual, registered o recruiter).
    """
    return user


def get_current_recruiter_dep(
    user: User = Depends(_get_current_recruiter),
) -> User:
    """
    Protege rutas exclusivas para reclutadores (crear/editar vacantes, evaluar postulantes).
    Lanza HTTP 403 Forbidden si el rol no es 'recruiter'.
    """
    return user


def get_current_candidate_dep(
    user: User = Depends(_get_current_candidate),
) -> User:
    """
    Protege rutas exclusivas para postulantes (subir CVs, aplicar a vacantes).
    Lanza HTTP 403 Forbidden si el rol no es 'candidate' o 'casual'.
    """
    return user
