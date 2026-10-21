from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.main import app
from app.models.application import Application
from app.models.job import Job
from app.models.resume import Resume
from app.models.user import User


def reset_database():
    db = SessionLocal()
    try:
        db.query(Application).delete()
        db.query(Resume).delete()
        db.query(Job).delete()
        db.query(User).delete()
        db.commit()
    finally:
        db.close()


def test_first_user_registers_as_admin():
    """Valida que el primer usuario registrado en el sistema obtenga el rol de administrador."""
    reset_database()

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "admin@example.com",
                "password": "123456",
                "full_name": "Admin Principal",
            },
        )

        assert response.status_code == 201, response.text
        payload = response.json()
        assert payload["role"] == "admin"
        assert payload["email"] == "admin@example.com"


def test_second_user_registers_as_standard_user():
    """Valida que los siguientes usuarios registrados no sean admin, sino usuarios estándar."""
    reset_database()

    with TestClient(app) as client:
        # Primer usuario (Admin)
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "admin@example.com",
                "password": "123456",
                "full_name": "Admin Principal",
            },
        )

        # Segundo usuario (Candidato / Usuario regular)
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "candidate@example.com",
                "password": "123456",
                "full_name": "Candidato Prueba",
            },
        )

        assert response.status_code == 201, response.text
        payload = response.json()
        # El rol por defecto para usuarios subsiguientes suele ser candidate o user
        assert payload["role"] != "admin"
        assert payload["email"] == "candidate@example.com"


def test_register_duplicate_email_fails():
    """Valida que el sistema rechace el registro con un correo electrónico ya existente."""
    reset_database()

    with TestClient(app) as client:
        user_data = {
            "email": "duplicado@example.com",
            "password": "123456",
            "full_name": "Usuario Uno",
        }

        # Registro exitoso la primera vez
        res1 = client.post("/api/v1/auth/register", json=user_data)
        assert res1.status_code == 201

        # Intento de registro con el mismo correo
        res2 = client.post("/api/v1/auth/register", json=user_data)
        assert res2.status_code in [400, 422], "Debe fallar por correo duplicado"


def test_admin_user_has_recruiter_access():
    """Valida el inicio de sesión del admin y el acceso a rutas protegidas con Token JWT."""
    reset_database()

    with TestClient(app) as client:
        register_response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "admin@example.com",
                "password": "123456",
                "full_name": "Admin Principal",
            },
        )
        assert register_response.status_code == 201, register_response.text

        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@example.com",
                "password": "123456",
            },
        )
        assert login_response.status_code == 200, login_response.text
        token = login_response.json()["access_token"]

        jobs_response = client.get(
            "/api/v1/jobs",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert jobs_response.status_code == 200, jobs_response.text


def test_login_invalid_credentials():
    """Valida que el inicio de sesión falle si la contraseña es incorrecta."""
    reset_database()

    with TestClient(app) as client:
        # Registrar usuario primero
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "correctpassword",
                "full_name": "Test User",
            },
        )

        # Intentar login con contraseña incorrecta
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "wrongpassword",
            },
        )
        assert response.status_code == 401, "Debe rechazar credenciales incorrectas"


def test_unauthorized_access_without_token():
    """Valida que las rutas protegidas nieguen el acceso si no se provee un token de autorización."""
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/jobs"
        )  # O cualquier ruta protegida de administración/creación
        # Dependiendo de si /api/v1/jobs permite lectura pública o no,
        # puedes usar una ruta estrictamente protegida como POST /api/v1/jobs
        post_response = client.post(
            "/api/v1/jobs", json={"title": "Vacante sin permiso"}
        )
        assert post_response.status_code in [401, 403], "Debe denegar acceso sin token"


def test_admin_can_register_recruiter():
    """Valida que un administrador autenticado pueda registrar con éxito a un nuevo reclutador."""
    reset_database()

    with TestClient(app) as client:
        # 1. Registrar al primer usuario (que automáticamente se vuelve 'admin')
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "admin@example.com",
                "password": "securepassword123",
                "full_name": "Administrador General",
            },
        )

        # 2. Hacer login como admin para obtener su token JWT
        login_res = client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@example.com",
                "password": "securepassword123",
            },
        )
        admin_token = login_res.json()["access_token"]

        # 3. El admin crea una cuenta de reclutador usando el endpoint protegido
        recruiter_res = client.post(
            "/api/v1/auth/register/recruiter",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "email": "recruiter@example.com",
                "password": "recruiterpassword123",
                "full_name": "Reclutador de Prueba",
            },
        )

        assert recruiter_res.status_code == 201, recruiter_res.text
        data = recruiter_res.json()
        assert data["email"] == "recruiter@example.com"
        assert data["role"] == "recruiter"


def test_non_admin_cannot_register_recruiter_fails():
    """Valida que un usuario común (no admin) no tenga permisos para registrar reclutadores."""
    reset_database()

    with TestClient(app) as client:
        # 1. Registrar al admin principal
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "admin@example.com",
                "password": "securepassword123",
                "full_name": "Administrador General",
            },
        )

        # 2. Registrar y loguear a un usuario normal / candidato
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "candidate@example.com",
                "password": "candidatepassword123",
                "full_name": "Candidato Común",
            },
        )
        login_res = client.post(
            "/api/v1/auth/login",
            json={
                "email": "candidate@example.com",
                "password": "candidatepassword123",
            },
        )
        candidate_token = login_res.json()["access_token"]

        # 3. Intentar registrar un reclutador usando el token del candidato (Debe fallar por permisos)
        response = client.post(
            "/api/v1/auth/register/recruiter",
            headers={"Authorization": f"Bearer {candidate_token}"},
            json={
                "email": "malicious_recruiter@example.com",
                "password": "password123",
                "full_name": "Intruso",
            },
        )

        # FastAPI / dependencias de seguridad deben retornar 401 o 403 al no ser admin
        assert response.status_code in [401, 403], response.text
