from types import SimpleNamespace

from app.api.v1.endpoints import jobs, resumes
from app.schemas.job import JobCreate
from app.schemas.resume import ResumeCreate


class FakeQuery:
    def filter(self, *_conditions):
        return self

    def options(self, *_options):
        return self

    def first(self):
        return None

    def all(self):
        return []


class FakeDatabase:
    def __init__(self):
        self.commits = 0
        self.added = []

    def query(self, _model):
        return FakeQuery()

    def add(self, instance):
        self.added.append(instance)

    def commit(self):
        self.commits += 1

    def refresh(self, _instance):
        pass

    def rollback(self):
        pass


def test_create_resume_generates_experience_embedding_after_persisting(monkeypatch):
    db = FakeDatabase()
    embedding = [0.25] * 384
    cached_skills = []

    monkeypatch.setattr(
        resumes,
        "ensure_skills_cached",
        lambda _db, skills: cached_skills.extend(skills),
    )

    def generate_after_commit(text):
        assert db.commits == 1
        assert text == "Construcción de APIs\nMantenimiento de servicios"
        return embedding

    monkeypatch.setattr(resumes, "generate_embedding", generate_after_commit)

    result = resumes.create_resume(
        ResumeCreate(
            candidate_email="candidate@example.com",
            parsed_data={
                "work_experience": [
                    "Construcción de APIs",
                    "Mantenimiento de servicios",
                ],
                "technical_skills": ["Python"],
                "soft_skills": ["Comunicación"],
            },
            extracted_skills=["Python", "Comunicación"],
        ),
        db,
        None,
    )

    assert result.embedding == embedding
    assert db.commits == 2
    assert cached_skills == ["Python", "Comunicación", "Python", "Comunicación"]


def test_create_job_generates_description_embedding_after_persisting(monkeypatch):
    db = FakeDatabase()
    embedding = [0.5] * 384
    cached_skills = []
    monkeypatch.setattr(
        jobs,
        "ensure_skills_cached",
        lambda _db, skills: cached_skills.extend(skills),
    )

    def generate_after_commit(text):
        assert db.commits == 1
        assert text == "Desarrollar y mantener servicios web."
        return embedding

    monkeypatch.setattr(jobs, "generate_embedding", generate_after_commit)

    result = jobs.create_job(
        JobCreate(
            title="Backend",
            area="Tecnología",
            profile_type="Backend",
            modality="remoto",
            description="Desarrollar y mantener servicios web.",
            technical_skills=["Python"],
            soft_skills=["Comunicación"],
        ),
        db,
        SimpleNamespace(id="recruiter-id"),
    )

    assert result.embedding == embedding
    assert db.commits == 2
    assert cached_skills == ["Python", "Comunicación"]
