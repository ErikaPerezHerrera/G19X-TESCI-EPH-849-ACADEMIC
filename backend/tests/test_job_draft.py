from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints import jobs
from app.schemas.job import JobDraftRequest


@pytest.mark.parametrize(
    ("result", "expected_available"),
    [
        (
            {
                "draft": {"title": "Desarrollador backend"},
                "ai_available": True,
            },
            True,
        ),
        (
            {"draft": {"title": ""}, "ai_available": False},
            False,
        ),
    ],
)
def test_draft_job_reports_ai_availability(monkeypatch, result, expected_available):
    monkeypatch.setattr(
        jobs,
        "generate_job_draft_with_status",
        lambda **_kwargs: result,
    )

    response = jobs.draft_job(
        JobDraftRequest(instruction="Vacante backend Python"),
        db=None,
        current_user=SimpleNamespace(role="recruiter"),
    )

    assert response["ai_available"] is expected_available


def test_draft_job_requires_instruction_or_source_text():
    with pytest.raises(HTTPException) as error:
        jobs.draft_job(
            JobDraftRequest(),
            db=None,
            current_user=SimpleNamespace(role="recruiter"),
        )

    assert error.value.status_code == 400
