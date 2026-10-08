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

    def first(self):
        return self.value


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
    )


def test_reopening_closed_job_updates_same_record(monkeypatch):
    job = make_job("closed")
    db = FakeDatabase(job)
    monkeypatch.setattr(jobs, "ensure_skills_cached", lambda *_args: None)
    deadline = datetime.now(timezone.utc) + timedelta(days=10)

    result = jobs.reopen_job(
        str(job.id),
        JobReopen(
            title="Desarrollador API",
            area="Ingeniería",
            profile_type="Backend",
            modality="remoto",
            location=None,
            description="Crear y mantener servicios API",
            technical_skills=["Python", "FastAPI"],
            soft_skills=["Comunicación"],
            deadline=deadline,
            benefits="Seguro médico",
        ),
        db,
        SimpleNamespace(id="recruiter-id"),
    )

    assert result is job
    assert result.id == job.id
    assert result.status == "active"
    assert result.title == "Desarrollador API"
    assert result.technical_skills == ["Python", "FastAPI"]
    assert db.committed


def test_reopening_expired_job_only_changes_deadline():
    job = make_job("expired")
    original_title = job.title
    db = FakeDatabase(job)
    deadline = datetime.now(timezone.utc) + timedelta(days=10)

    result = jobs.reopen_job(
        str(job.id),
        JobReopen(deadline=deadline),
        db,
        SimpleNamespace(id="recruiter-id"),
    )

    assert result.status == "active"
    assert result.title == original_title
    assert result.deadline == deadline
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
