from fastapi.testclient import TestClient
from unittest.mock import patch
from datetime import datetime, timezone, timedelta

from app.core.database import SessionLocal
from app.main import app


def get_auth_token_for_user(
    client: TestClient, email: str, role_password: str = "securepassword123"
) -> str:
    """Registra un usuario y retorna su token JWT de acceso."""
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": role_password,
            "full_name": "Usuario Test",
        },
    )
    res = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": role_password,
        },
    )
    return res.json()["access_token"]


def create_mock_resume_and_job(
    client: TestClient,
    recruiter_token: str,
    candidate_email: str = "candidate@example.com",
):
    """Función de apoyo para crear un CV y una Vacante activa en la BD de pruebas."""
    from app.models.user import User
    from app.models.resume import Resume

    db = SessionLocal()
    try:
        user_res = db.query(User).filter(User.email == candidate_email).first()
        user_id = str(user_res.id) if user_res else None

        resume = Resume(
            candidate_email=candidate_email,
            parsed_data={
                "professional_title": "Python Developer",
                "technical_skills": ["Python", "FastAPI"],
                "soft_skills": ["Comunicación"],
            },
            user_id=user_id,
        )
        db.add(resume)
        db.commit()
        db.refresh(resume)
        resume_id = str(resume.id)

        future_deadline = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
        with patch(
            "app.api.v1.endpoints.jobs.generate_embedding", return_value=[0.1] * 384
        ):
            job_res = client.post(
                "/api/v1/jobs",
                headers={"Authorization": f"Bearer {recruiter_token}"},
                json={
                    "title": "Backend Engineer",
                    "area": "Tecnología",
                    "profile_type": "Senior",
                    "modality": "remoto",
                    "description": "Buscamos desarrollador experto en Python y FastAPI.",
                    "technical_skills": ["Python", "FastAPI"],
                    "soft_skills": ["Comunicación"],
                    "status": "active",
                    "deadline": future_deadline,
                },
            )
        job_id = job_res.json()["id"]
        return resume_id, job_id
    finally:
        db.close()


def test_create_application_success():
    """Valida que un candidato pueda postularse exitosamente a una vacante activa."""
    with TestClient(app) as client:
        recruiter_token = get_auth_token_for_user(client, "recruiter@example.com")
        candidate_email = "candidate@example.com"
        candidate_token = get_auth_token_for_user(client, candidate_email)

        resume_id, job_id = create_mock_resume_and_job(
            client, recruiter_token, candidate_email
        )

        with patch(
            "app.api.v1.endpoints.applications.recalculate_application_match",
            return_value=None,
        ):
            response = client.post(
                f"/api/v1/jobs/{job_id}/applications",
                headers={"Authorization": f"Bearer {candidate_token}"},
                json={
                    "resume_id": resume_id,
                    "candidate_email": candidate_email,
                },
            )

        assert response.status_code == 201, response.text
        data = response.json()
        assert data["job_id"] == job_id
        assert data["candidate_email"] == candidate_email
        assert data["status"] == "received"


def test_create_application_email_mismatch_fails():
    """Valida que falle la postulación si el correo ingresado no coincide con el del CV."""
    with TestClient(app) as client:
        recruiter_token = get_auth_token_for_user(client, "recruiter@example.com")
        resume_id, job_id = create_mock_resume_and_job(
            client, recruiter_token, "correct@example.com"
        )

        response = client.post(
            f"/api/v1/jobs/{job_id}/applications",
            json={
                "resume_id": resume_id,
                "candidate_email": "wrong@example.com",
            },
        )

        assert response.status_code == 422
        assert "correo de la postulación debe coincidir" in response.json()["detail"]


def test_duplicate_application_fails():
    """Valida que no se permita postularse dos veces a la misma vacante con el mismo correo."""
    with TestClient(app) as client:
        recruiter_token = get_auth_token_for_user(client, "recruiter@example.com")
        email = "candidate@example.com"
        resume_id, job_id = create_mock_resume_and_job(client, recruiter_token, email)

        payload = {
            "resume_id": resume_id,
            "candidate_email": email,
        }

        with patch(
            "app.api.v1.endpoints.applications.recalculate_application_match",
            return_value=None,
        ):
            res1 = client.post(f"/api/v1/jobs/{job_id}/applications", json=payload)
            assert res1.status_code == 201

            res2 = client.post(f"/api/v1/jobs/{job_id}/applications", json=payload)
            assert res2.status_code == 409
            assert "Ya existe una postulación" in res2.json()["detail"]


def test_list_my_applications():
    """Valida que un usuario registrado pueda consultar su lista personal de postulaciones."""
    with TestClient(app) as client:
        recruiter_token = get_auth_token_for_user(client, "recruiter@example.com")
        candidate_email = "candidate@example.com"
        candidate_token = get_auth_token_for_user(client, candidate_email)

        resume_id, job_id = create_mock_resume_and_job(
            client, recruiter_token, candidate_email
        )

        with patch(
            "app.api.v1.endpoints.applications.recalculate_application_match",
            return_value=None,
        ):
            client.post(
                f"/api/v1/jobs/{job_id}/applications",
                headers={"Authorization": f"Bearer {candidate_token}"},
                json={"resume_id": resume_id, "candidate_email": candidate_email},
            )

        response = client.get(
            "/api/v1/applications/me",
            headers={"Authorization": f"Bearer {candidate_token}"},
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert len(data) == 1
        assert data[0]["job_id"] == job_id


def test_recruiter_lists_and_rejects_application():
    """Valida que el reclutador pueda listar los candidatos de una vacante y rechazar uno."""
    with TestClient(app) as client:
        recruiter_token = get_auth_token_for_user(client, "recruiter@example.com")
        candidate_email = "candidate@example.com"
        resume_id, job_id = create_mock_resume_and_job(
            client, recruiter_token, candidate_email
        )

        with patch(
            "app.api.v1.endpoints.applications.recalculate_application_match",
            return_value=None,
        ):
            create_app_res = client.post(
                f"/api/v1/jobs/{job_id}/applications",
                json={"resume_id": resume_id, "candidate_email": candidate_email},
            )
        application_id = create_app_res.json()["id"]

        list_res = client.post(  # o get según tu ruta de listado
            f"/api/v1/jobs/{job_id}/applications",
            headers={"Authorization": f"Bearer {recruiter_token}"},
        )
        # Nota: ajusta si tu listado usa GET
        list_get_res = client.get(
            f"/api/v1/jobs/{job_id}/applications",
            headers={"Authorization": f"Bearer {recruiter_token}"},
        )
        assert list_get_res.status_code == 200
        assert len(list_get_res.json()) == 1

        reject_res = client.patch(
            f"/api/v1/applications/{application_id}/reject",
            headers={"Authorization": f"Bearer {recruiter_token}"},
            json={
                "rejection_reason": "El perfil no se alinea con la experiencia requerida."
            },
        )
        assert reject_res.status_code == 200, reject_res.text
        assert reject_res.json()["status"] == "rejected"
        assert reject_res.json()["rejection_reason"] is not None
