import uuid
from fastapi.testclient import TestClient
from unittest.mock import patch
from datetime import datetime, timezone, timedelta

from app.core.database import SessionLocal
from app.main import app
from app.models.application import Application
from app.models.job import Job
from app.models.user import User

from app.services.autostore_job import auto_archive_expired_closed_jobs


def reset_database():
    db = SessionLocal()
    try:
        db.query(Application).delete()
        db.query(Job).delete()
        db.query(User).delete()
        db.commit()
    finally:
        db.close()


def get_auth_token_for_recruiter(
    client: TestClient, email: str = "recruiter@example.com"
    ) -> str:
    """Función auxiliar para registrar un usuario y obtener su token JWT."""
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "securepassword123",
            "full_name": "Reclutador Test",
        },
    )
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "securepassword123",
        },
    )
    return response.json()["access_token"]


def get_auth_token_for_admin(
    client: TestClient, email: str = "admin@example.com"
    ) -> str:
    """Registra al primer usuario y fuerza su rol a 'admin' en la base de datos."""
    token = get_auth_token_for_recruiter(client, email)

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.role = "admin"
            db.commit()
    finally:
        db.close()

    return token


def test_create_job_success():
    """Valida que un reclutador autenticado pueda crear una vacante de manera exitosa."""
    reset_database()

    with TestClient(app) as client:
        token = get_auth_token_for_recruiter(client)

        future_deadline = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()

        with patch(
            "app.api.v1.endpoints.jobs.generate_embedding", return_value=[0.1] * 384
        ):
            response = client.post(
                "/api/v1/jobs",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "title": "Desarrollador Python Senior",
                    "area": "Tecnología",
                    "profile_type": "Senior",
                    "modality": "remoto",
                    "location": None,
                    "description": "Buscamos experto en FastAPI y PostgreSQL con amplia experiencia.",
                    "technical_skills": ["Python", "FastAPI", "PostgreSQL"],
                    "soft_skills": ["Liderazgo"],
                    "status": "active",
                    "deadline": future_deadline,
                    "benefits": "Trabajo 100% remoto, seguro de gastos médicos.",
                },
            )

        assert response.status_code == 201, response.text
        data = response.json()
        assert data["title"] == "Desarrollador Python Senior"
        assert data["status"] == "active"
        assert "id" in data


def test_list_and_filter_jobs():
    """Valida que se puedan listar las vacantes y filtrarlas por estado."""
    reset_database()

    with TestClient(app) as client:
        token = get_auth_token_for_recruiter(client)

        with patch(
            "app.api.v1.endpoints.jobs.generate_embedding", return_value=[0.1] * 384
        ):
            client.post(
                "/api/v1/jobs",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "title": "Vacante Activa",
                    "area": "IT",
                    "profile_type": "Junior",
                    "modality": "remoto",
                    "description": "Descripción larga de prueba para la vacante activa.",
                    "technical_skills": ["Python"],
                    "soft_skills": [],
                    "status": "active",
                },
            )

        response = client.get("/api/v1/jobs")
        assert response.status_code == 200
        jobs = response.json()
        assert len(jobs) == 1
        assert jobs[0]["title"] == "Vacante Activa"

        response_filtered = client.get("/api/v1/jobs?status=active")
        assert response_filtered.status_code == 200
        assert len(response_filtered.json()) == 1


def test_get_job_by_id_not_found():
    """Valida que consultar una vacante inexistente devuelva un error 404."""
    reset_database()
    with TestClient(app) as client:
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/api/v1/jobs/{fake_uuid}")
        assert response.status_code == 404
        assert response.json()["detail"] == "Vacante no encontrada"


def test_close_job_success():
    """Valida que un reclutador pueda cerrar una vacante correctamente."""
    reset_database()

    with TestClient(app) as client:
        token = get_auth_token_for_recruiter(client)

        with patch(
            "app.api.v1.endpoints.jobs.generate_embedding", return_value=[0.1] * 384
        ):
            create_res = client.post(
                "/api/v1/jobs",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "title": "Vacante a Cerrar",
                    "area": "IT",
                    "profile_type": "Semi-Senior",
                    "modality": "presencial",
                    "location": "CDMX",
                    "description": "Descripción detallada para la vacante a cerrar próximamente.",
                    "technical_skills": ["Java"],
                    "soft_skills": ["Comunicación"],
                    "status": "active",
                },
            )
        job_id = create_res.json()["id"]

        close_res = client.patch(
            f"/api/v1/jobs/{job_id}/close",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert close_res.status_code == 200, close_res.text
        assert close_res.json()["status"] == "closed"


def test_store_job_as_admin_success():
    """Valida que un administrador pueda cambiar el estado de una vacante cerrada a 'stored' (200)."""
    reset_database()

    with TestClient(app) as client:
        recruiter_token = get_auth_token_for_recruiter(client, "recruiter@example.com")

        with patch(
            "app.api.v1.endpoints.jobs.generate_embedding", return_value=[0.1] * 384
        ):
            create_res = client.post(
                "/api/v1/jobs",
                headers={"Authorization": f"Bearer {recruiter_token}"},
                json={
                    "title": "Vacante a Almacenar",
                    "area": "IT",
                    "profile_type": "Senior",
                    "modality": "remoto",
                    "description": "Descripción detallada para la vacante a almacenar.",
                    "technical_skills": ["Python"],
                    "soft_skills": [],
                    "status": "active",
                },
            )
        job_id = create_res.json()["id"]

        client.patch(
            f"/api/v1/jobs/{job_id}/close",
            headers={"Authorization": f"Bearer {recruiter_token}"},
        )

        admin_token = get_auth_token_for_admin(client, "admin@example.com")

        store_res = client.patch(
            f"/api/v1/jobs/{job_id}/store",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert store_res.status_code == 200, store_res.text
        assert store_res.json()["status"] == "stored"


def test_store_job_as_recruiter_forbidden():
    """Valida que un reclutador común no pueda almacenar una vacante (403)."""
    reset_database()

    with TestClient(app) as client:
        # 1. Creamos un admin primero para ocupar el primer registro
        get_auth_token_for_admin(client, "admin@example.com")

        # 2. Creamos al reclutador (segundo usuario registrado, rol de reclutador real)
        recruiter_email = "recruiter@example.com"
        client.post(
            "/api/v1/auth/register",
            json={
                "email": recruiter_email,
                "password": "securepassword123",
                "full_name": "Reclutador Test",
            },
        )

        # Forzamos su rol explícitamente a "recruiter"
        db = SessionLocal()
        try:
            recruiter_user = (
                db.query(User).filter(User.email == recruiter_email).first()
            )
            if recruiter_user:
                recruiter_user.role = "recruiter"
                db.commit()
        finally:
            db.close()

        login_res = client.post(
            "/api/v1/auth/login",
            json={
                "email": recruiter_email,
                "password": "securepassword123",
            },
        )
        recruiter_token = login_res.json()["access_token"]

        with patch(
            "app.api.v1.endpoints.jobs.generate_embedding", return_value=[0.1] * 384
        ):
            create_res = client.post(
                "/api/v1/jobs",
                headers={"Authorization": f"Bearer {recruiter_token}"},
                json={
                    "title": "Vacante Cerrada",
                    "area": "IT",
                    "profile_type": "Senior",
                    "modality": "remoto",
                    "description": "Descripción detallada para la prueba de permisos.",
                    "technical_skills": ["Python"],
                    "soft_skills": [],
                    "status": "active",
                },
            )
        job_id = create_res.json()["id"]

        client.patch(
            f"/api/v1/jobs/{job_id}/close",
            headers={"Authorization": f"Bearer {recruiter_token}"},
        )

        # Intentar almacenar usando el token de reclutador (debe fallar con 403)
        store_res = client.patch(
            f"/api/v1/jobs/{job_id}/store",
            headers={"Authorization": f"Bearer {recruiter_token}"},
        )

        assert store_res.status_code == 403
        assert "Se requiere rol de administrador" in store_res.json()["detail"]


def test_store_active_job_conflict():
    """Valida que un administrador no pueda almacenar una vacante que todavía se encuentra activa (409)."""
    reset_database()

    with TestClient(app) as client:
        recruiter_token = get_auth_token_for_recruiter(client, "recruiter@example.com")

        with patch(
            "app.api.v1.endpoints.jobs.generate_embedding", return_value=[0.1] * 384
        ):
            create_res = client.post(
                "/api/v1/jobs",
                headers={"Authorization": f"Bearer {recruiter_token}"},
                json={
                    "title": "Vacante Activa",
                    "area": "IT",
                    "profile_type": "Senior",
                    "modality": "remoto",
                    "description": "Descripción detallada para la vacante activa.",
                    "technical_skills": ["Python"],
                    "soft_skills": [],
                    "status": "active",
                },
            )
        job_id = create_res.json()["id"]

        admin_token = get_auth_token_for_admin(client, "admin@example.com")

        store_res = client.patch(
            f"/api/v1/jobs/{job_id}/store",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert store_res.status_code == 409
        assert (
            "Solo se pueden almacenar vacantes que se encuentren en estado cerrado"
            in store_res.json()["detail"]
        )


def test_list_jobs_unauthenticated_draft_forced_to_active():
    """Valida que un usuario sin sesión que solicite un estado restringido (como draft)
    sea limitado o forzado a ver únicamente vacantes activas."""
    reset_database()

    with TestClient(app) as client:
        token = get_auth_token_for_recruiter(client)

        # Crear una vacante en estado 'draft' (o simulando un borrador)
        with patch(
            "app.api.v1.endpoints.jobs.generate_embedding", return_value=[0.1] * 384
        ):
            client.post(
                "/api/v1/jobs",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "title": "Borrador Interno",
                    "area": "IT",
                    "profile_type": "Senior",
                    "modality": "remoto",
                    "description": "Descripción del borrador interno de prueba.",
                    "technical_skills": ["Python"],
                    "soft_skills": [],
                    "status": "draft",
                },
            )

        # Intentar listar con ?status=draft sin enviar token de autenticación
        response = client.get("/api/v1/jobs?status=draft")

        assert response.status_code == 200
        # Al no ser personal autorizado, el backend fuerza el filtro a 'active' o ignora el draft,
        # por lo que no debe retornar el borrador.
        jobs = response.json()
        assert len(jobs) == 0


def test_auto_archive_expired_closed_jobs_success(db_session, client):
    """
    Valida que la función de auto-archivado detecte vacantes cerradas hace más de 30 días,
    elimine sus postulaciones (liberando slots) y cambie su estado a 'stored'.
    """
    # 0. Registrar el reclutador usando el helper existente para evitar problemas con los campos del modelo
    get_auth_token_for_recruiter(client, email="auto_recruiter@example.com")

    # Obtener el usuario creado desde la sesión de la base de datos de pruebas
    recruiter_user = (
        db_session.query(User)
        .filter(User.email == "auto_recruiter@example.com")
        .first()
    )

    # 1. Crear una vacante simulada con el ID del reclutador obtenido
    expired_job = Job(
        id=uuid.uuid4(),
        title="Vacante Antigua Cerrada",
        area="IT",
        profile_type="Junior",
        modality="remoto",
        description="Esta vacante lleva cerrada más de 30 días para pruebas de auto-archivado.",
        status="closed",
        recruiter_id=recruiter_user.id,  # <--- ID válido garantizado
    )
    db_session.add(expired_job)
    db_session.commit()
    db_session.refresh(expired_job)

    # 2. Forzar artificialmente el campo updated_at a hace 31 días atrás
    expired_job.updated_at = datetime.now(timezone.utc) - timedelta(days=31)
    db_session.commit()

    # 3. Ejecutar la función de auto-archivado
    auto_archive_expired_closed_jobs(db_session)
    db_session.refresh(expired_job)

    # 4. Aserciones para comprobar que el estado cambió a 'stored'
    assert expired_job.status == "stored"
