from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints import jobs
from app.schemas.job import JobReopen


class FakeQuery:
    def __init__(self, value):
        self.value = value

    def filter(self, *_conditions):
        return self

    def options(self, *_options):
        return self

    def first(self):
        return self.value

    def all(self):
        return []

    def delete(self, synchronize_session=False):
        return 0


class FakeDatabase:
    def __init__(self, job):
        self.job = job
        self.committed = False
        self.rolled_back = False

    def query(self, _model):
        return FakeQuery(self.job)

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
    monkeypatch.setattr(jobs, "ensure_skills_cached", lambda *_args: None)

    def fail_if_embedding_is_generated(_text):
        raise AssertionError(
            "No se debe recalcular el embedding si solo se actualiza la fecha límite al reabrir."
        )

    monkeypatch.setattr(jobs, "generate_embedding", fail_if_embedding_is_generated)
    deadline = datetime.now(timezone.utc) + timedelta(days=10)

    result = jobs.reopen_job(
        str(job.id),
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

    def fail_if_embedding_is_generated(_text):
        raise AssertionError(
            "No se debe recalcular el embedding de una vacante vencida."
        )

    monkeypatch.setattr(jobs, "generate_embedding", fail_if_embedding_is_generated)
    deadline = datetime.now(timezone.utc) + timedelta(days=10)

    result = jobs.reopen_job(
        str(job.id),
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

    result = jobs.close_job(
        str(job.id),
        db,
        SimpleNamespace(id="different-recruiter-id", role="recruiter"),
    )

    assert result is job
    assert result.status == "closed"
    assert db.committed


def test_expired_job_cannot_be_reopened_without_future_deadline():
    job = make_job("expired")
    db = FakeDatabase(job)

    with pytest.raises(HTTPException) as error:
        jobs.reopen_job(
            str(job.id),
            JobReopen(deadline=datetime.now(timezone.utc) - timedelta(days=1)),
            db,
            SimpleNamespace(id="recruiter-id"),
        )

    assert error.value.status_code == 422
    assert not db.committed


def test_expired_job_rejects_changes_to_job_fields():
    job = make_job("expired")
    db = FakeDatabase(job)

    with pytest.raises(HTTPException) as error:
        jobs.reopen_job(
            str(job.id),
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
    monkeypatch.setattr(jobs, "ensure_skills_cached", lambda *_args: None)

    result = jobs.reopen_job(
        str(job.id),
        JobReopen(deadline=None),
        db,
        SimpleNamespace(id="different-recruiter-id", role="recruiter"),
    )

    assert result is job
    assert result.status == "active"
    assert result.deadline is None
    assert db.committed
