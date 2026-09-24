## Estas funciones actúan como "guardianes" (middlewares/guards) en las rutas de FastAPI. 
## Cuando pasan como parámetros dentro de Depends(...), FastAPI ejecuta toda la cadena de validación antes de correr el código del endpoint

from fastapi import Depends

from app.core.security import get_current_user, get_current_recruiter
from app.models.user import User


def get_current_user_dep(
    user: User = Depends(get_current_user),
) -> User:
    """
    Dependencia de FastAPI para proteger rutas que requieren cualquier usuario autenticado
    (candidatos registrados o reclutadores).

    1. 'db': Inyecta una sesión activa de la base de datos PostgreSQL a través de 'get_db'.
    2. 'user': Decodifica el token JWT enviado en los encabezados HTTP (Header Authorization)
       y obtiene la instancia del usuario desde la base de datos a través de 'get_current_user'.
    
    Retorna:
        User: El objeto del usuario autenticado actual.
    """
    return user


def get_current_recruiter_dep(
    user: User = Depends(get_current_recruiter),
) -> User:
    """
    Dependencia de FastAPI para proteger rutas exclusivas de reclutadores
    (como crear vacantes, ver candidatos o descartar postulaciones).

    1. 'db': Inyecta la sesión de la base de datos.
    2. 'user': Ejecuta 'get_current_recruiter', el cual primero valida el token JWT
       y luego verifica que el rol del usuario sea 'recruiter' o 'admin'. Si no tiene
       el rol adecuado, FastAPI lanzará un error HTTP 403 (Forbidden).

    Retorna:
        User: El objeto del reclutador autenticado actual.
    """
    return user
