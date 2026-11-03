from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from fastapi.testclient import TestClient
from uuid import uuid4

import pytest
from fastapi import HTTPException, BackgroundTasks
from app.core.database import SessionLocal
from unittest.mock import patch

from app.api.v1.endpoints import jobs
from app.schemas.job import JobReopen
from app.models.application import Application

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


class FakeQuery:
    def __init__(self, value, model=None, filter_conditions=None):
        self.value = value
        self.model = model
        self.filter_conditions = filter_conditions or []

    def filter(self, *conditions):
        return FakeQuery(
            self.value,
            model=self.model,
            filter_conditions=self.filter_conditions + list(conditions),
        )

    def options(self, *_options):
        return self

    def first(self):
        from app.models.email_template import EmailTemplate
        from app.models.application import Application

        if self.model == EmailTemplate:
            return SimpleNamespace(
                template_key="status_update",
                subject="Actualización de vacante: {{job_title}}",
                body_text="Hola {{candidate_name}}, la vacante {{job_title}} ha sido actualizada. {{message}}",
            )
        if self.model == Application:
            return None
        return self.value

    def all(self):
        from app.models.application import Application

        if self.model == Application:
            return [
                SimpleNamespace(
                    id=uuid4(),
                    candidate_email="candidato_prueba@example.com",
                    status="applied",
                )
            ]
        return [self.value] if self.value else []

    def delete(self, synchronize_session=False):
        return 0


class FakeDatabase:
    def __init__(self, job, has_hired_application=False):
        self.job = job
        self.has_hired_application = has_hired_application
        self.committed = False
        self.rolled_back = False
        self.deleted_instances = []

    def query(self, model):
        from app.models.email_template import EmailTemplate
        from app.models.application import Application

        if model == EmailTemplate:
            return FakeQuery(None, model=EmailTemplate)
        if model == Application:
            return FakeQuery(self.job, model=Application)
        return FakeQuery(self.job, model=model)

    def delete(self, instance):
        self.deleted_instances.append(instance)

    def commit(self):
        self.committed = True

    def refresh(self, _job):
        pass

    def rollback(self):
        self.rolled_back = True


def make_job(status):
    return SimpleNamespace(
        id=uuid4(),
        recruiter_id="recruiter-id",
        status=status,
        title="Desarrollador",
        area="Tecnología",
        profile_type="Backend",
        modality="remoto",
        location=None,
        description="Desarrollo de servicios web",
        technical_skills=["Python"],
        soft_skills=["Comunicación"],
        deadline=None,
        benefits=None,
        embedding=[0.4] * 384,
    )

def test_reopening_closed_job_updates_same_record(monkeypatch):
    """Valida que al reabrir una vacante cerrada se actualice correctamente manteniendo la política de solo deadline."""
    job = make_job("closed")
    original_title = job.title
    existing_embedding = job.embedding
    db = FakeDatabase(job)
    bg_tasks = BackgroundTasks()
    monkeypatch.setattr(jobs, "ensure_skills_cached", lambda *_args: None)

    def fail_if_embedding_is_generated(_text):
        raise AssertionError(
            "No se debe recalcular el embedding si solo se actualiza la fecha límite al reabrir."
        )

    monkeypatch.setattr(jobs, "generate_embedding", fail_if_embedding_is_generated)
    deadline = datetime.now(timezone.utc) + timedelta(days=10)

    result = jobs.reopen_job(
        str(job.id),
        bg_tasks,
        JobReopen(deadline=deadline),
        db,
        SimpleNamespace(id="different-recruiter-id", role="recruiter"),
    )

    assert result is job
    assert result.id == job.id
    assert result.status == "active"
    assert result.title == original_title
    assert result.deadline == deadline
    assert result.embedding == existing_embedding
    assert db.committed


def test_reopening_expired_job_only_changes_deadline(monkeypatch):
    job = make_job("expired")
    existing_embedding = [0.4] * 384
    job.embedding = existing_embedding
    original_title = job.title
    db = FakeDatabase(job)
    bg_tasks = BackgroundTasks()

    def fail_if_embedding_is_generated(_text):
        raise AssertionError(
            "No se debe recalcular el embedding de una vacante vencida."
        )

    monkeypatch.setattr(jobs, "generate_embedding", fail_if_embedding_is_generated)
    deadline = datetime.now(timezone.utc) + timedelta(days=10)

    result = jobs.reopen_job(
        str(job.id),
        bg_tasks,
        JobReopen(deadline=deadline),
        db,
        SimpleNamespace(id="different-recruiter-id", role="recruiter"),
    )

    assert result.status == "active"
    assert result.title == original_title
    assert result.deadline == deadline
    assert result.embedding == existing_embedding
    assert db.committed


def test_recruiter_can_close_an_expired_job_created_by_another_recruiter():
    job = make_job("expired")
    db = FakeDatabase(job)
    bg_tasks = BackgroundTasks()

    result = jobs.close_job(
        str(job.id),
        bg_tasks,
        db,
        SimpleNamespace(id="different-recruiter-id", role="recruiter"),
    )

    assert result is job
    assert result.status == "closed"
    assert db.committed


def test_expired_job_cannot_be_reopened_without_future_deadline():
    job = make_job("expired")
    db = FakeDatabase(job)
    bg_tasks = BackgroundTasks()

    with pytest.raises(HTTPException) as error:
        jobs.reopen_job(
            str(job.id),
            bg_tasks,
            JobReopen(deadline=datetime.now(timezone.utc) - timedelta(days=1)),
            db,
            SimpleNamespace(id="recruiter-id"),
        )

    assert error.value.status_code == 422
    assert not db.committed


def test_expired_job_rejects_changes_to_job_fields():
    job = make_job("expired")
    db = FakeDatabase(job)
    bg_tasks = BackgroundTasks()

    with pytest.raises(HTTPException) as error:
        jobs.reopen_job(
            str(job.id),
            bg_tasks,
            JobReopen(
                deadline=datetime.now(timezone.utc) + timedelta(days=10),
                title="Otro título",
            ),
            db,
            SimpleNamespace(id="recruiter-id"),
        )

    assert error.value.status_code == 422
    assert not db.committed


def test_reopening_job_with_null_deadline(monkeypatch):
    """Valida que una vacante se pueda reabrir exitosamente sin especificar una fecha límite (deadline=None)."""
    job = make_job("closed")
    db = FakeDatabase(job)
    bg_tasks = BackgroundTasks()
    monkeypatch.setattr(jobs, "ensure_skills_cached", lambda *_args: None)

    result = jobs.reopen_job(
        str(job.id),
        bg_tasks,
        JobReopen(deadline=None),
        db,
        SimpleNamespace(id="different-recruiter-id", role="recruiter"),
    )

    assert result is job
    assert result.status == "active"
    assert result.deadline is None
    assert db.committed


def test_reopening_job_triggers_email_notification(monkeypatch):
    """Valida que al reabrir una vacante se invoque el servicio de envío de correos a los postulantes."""
    job = make_job("closed")
    db = FakeDatabase(job)
    bg_tasks = BackgroundTasks()

    monkeypatch.setattr(jobs, "ensure_skills_cached", lambda *_args: None)

    email_sent_mock = []

    def mock_send_email(to_email, subject, body_text):
        email_sent_mock.append({"to": to_email, "subject": subject, "body": body_text})
        return True

    monkeypatch.setattr("app.api.v1.endpoints.jobs.send_email", mock_send_email)

    deadline = datetime.now(timezone.utc) + timedelta(days=10)

    result = jobs.reopen_job(
        str(job.id),
        bg_tasks,
        JobReopen(deadline=deadline),
        db,
        SimpleNamespace(id="different-recruiter-id", role="recruiter"),
    )

    assert result.status == "active"
    assert db.committed

    for task in bg_tasks.tasks:
        task.func(*task.args, **task.kwargs)

    assert len(email_sent_mock) == 1
    assert email_sent_mock[0]["to"] == "candidato_prueba@example.com"


def test_stored_job_cannot_be_closed_fails():
    """Valida que una vacante que se encuentra en estado 'stored' (archivada) no pueda ser cerrada y devuelva un error 409 Conflict."""
    job = make_job("stored")
    db = FakeDatabase(job)
    bg_tasks = BackgroundTasks()

    with pytest.raises(HTTPException) as error:
        jobs.close_job(
            str(job.id),
            bg_tasks,
            db,
            SimpleNamespace(id="recruiter-id", role="recruiter"),
        )

    assert error.value.status_code == 409
    assert (
        "archivada" in error.value.detail.lower()
        or "stored" in error.value.detail.lower()
    )
    assert not db.committed


def test_reopen_job_with_hired_candidate(client):
    recruiter_token = get_auth_token_for_user(client, "recruiter@example.com")
    cand_email = "cand1@example.com"
    cand_token = get_auth_token_for_user(client, cand_email)
    resume_id, job_id = create_mock_resume_and_job(client, recruiter_token, cand_email)

    # 1. Postular candidato
    with patch(
        "app.api.v1.endpoints.applications.recalculate_application_match",
        return_value=None,
    ):
        app_res = client.post(
            f"/api/v1/jobs/{job_id}/applications",
            headers={"Authorization": f"Bearer {cand_token}"},
            json={"resume_id": resume_id, "candidate_email": cand_email},
        )
    assert app_res.status_code == 201
    app_id = app_res.json()["id"]

    # 2. Ciclo de estados hasta hired (cierra la vacante automáticamente)
    client.patch(
        f"/api/v1/applications/{app_id}/view",
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    client.patch(
        f"/api/v1/applications/{app_id}/interview",
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    hire_res = client.patch(
        f"/api/v1/applications/{app_id}/hire",
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert hire_res.status_code == 200
    assert hire_res.json()["status"] == "hired"

    # 3. Reabrir la vacante y comprobar la respuesta y el envío de correos
    sent = []
    with patch(
        "app.api.v1.endpoints.jobs.send_email",
        side_effect=lambda to, s, b: sent.append(to) or True,
    ):
        res = client.patch(
            f"/api/v1/jobs/{job_id}/reopen",
            headers={"Authorization": f"Bearer {recruiter_token}"},
            json={},
        )

    assert res.status_code == 200, res.text
    assert res.json()["status"] == "active"
    assert sent.count(cand_email) == 1
