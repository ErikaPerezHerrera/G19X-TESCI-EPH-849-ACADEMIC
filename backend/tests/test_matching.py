from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.main import app
from app.models.user import User


def reset_users():
    db = SessionLocal()
    try:
        db.query(User).delete()
        db.commit()
    finally:
        db.close()


def test_first_user_registers_as_admin():
    reset_users()

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


def test_admin_user_has_recruiter_access():
    reset_users()

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
