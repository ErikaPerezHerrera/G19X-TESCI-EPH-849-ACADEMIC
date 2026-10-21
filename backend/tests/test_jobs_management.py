from fastapi.testclient import TestClient
from unittest.mock import patch
from datetime import datetime, timezone, timedelta

from app.core.database import SessionLocal
from app.main import app
from app.models.application import Application
from app.models.job import Job
from app.models.user import User


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
    """Función auxiliar para registrar un usuario (admin/reclutador) y obtener su token JWT."""
    # Registrar
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "securepassword123",
            "full_name": "Reclutador Test",
        },
    )
    # Login
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "securepassword123",
        },
    )
    return response.json()["access_token"]


def test_create_job_success():
    """Valida que un reclutador autenticado pueda crear una vacante de manera exitosa."""
    reset_database()

    with TestClient(app) as client:
        token = get_auth_token_for_recruiter(client)

        future_deadline = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()

        # Mockeamos la generación de embeddings para agilizar el test de integración del endpoint
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
            # Crear una vacante activa
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

        # Listar sin filtros
        response = client.get("/api/v1/jobs")
        assert response.status_code == 200
        jobs = response.json()
        assert len(jobs) == 1
        assert jobs[0]["title"] == "Vacante Activa"

        # Listar con filtro por estado
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

        # Cerrar la vacante
        close_res = client.patch(
            f"/api/v1/jobs/{job_id}/close",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert close_res.status_code == 200, close_res.text
        assert close_res.json()["status"] == "closed"
