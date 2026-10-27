from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException, BackgroundTasks

from app.api.v1.endpoints import jobs
from app.schemas.job import JobReopen


class FakeQuery:
    def __init__(self, value, model=None):
        self.value = value
        self.model = model

    def filter(self, *_conditions):
        return self

    def options(self, *_options):
        return self

    def first(self):
        from app.models.email_template import EmailTemplate

        if self.model == EmailTemplate:
            return SimpleNamespace(
                template_key="status_update",
                subject="Actualización de vacante: {{job_title}}",
                body_text="Hola {{candidate_name}}, la vacante {{job_title}} ha sido actualizada. {{message}}",
            )
        return self.value

    def all(self):
        from app.models.application import Application

        if self.model == Application:
            # Retornar una lista con postulaciones simuladas para que el bucle de correo funcione
            return [SimpleNamespace(candidate_email="candidato_prueba@example.com")]
        return [self.value] if self.value else []

    def delete(self, synchronize_session=False):
        return 0


class FakeDatabase:
    def __init__(self, job):
        self.job = job
        self.committed = False
        self.rolled_back = False

    def query(self, model):
        from app.models.email_template import EmailTemplate
        from app.models.application import Application

        if model == EmailTemplate:
            return FakeQuery(None, model=EmailTemplate)
        if model == Application:
            return FakeQuery(self.job, model=Application)
        return FakeQuery(self.job, model=model)

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

    # Interceptamos send_email que es el que ahora ejecuta BackgroundTasks
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

    # Como BackgroundTasks acumula las tareas, podemos ejecutarlas manualmente para verificar el mock
    for task in bg_tasks.tasks:
        task.func(*task.args, **task.kwargs)

    assert len(email_sent_mock) == 1
    assert email_sent_mock[0]["to"] == "candidato_prueba@example.com"
