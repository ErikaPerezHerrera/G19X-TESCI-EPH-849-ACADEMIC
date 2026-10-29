from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from unittest.mock import patch

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
        assert data["status"] == "application_received"


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
        candidate_token = get_auth_token_for_user(client, email)
        resume_id, job_id = create_mock_resume_and_job(client, recruiter_token, email)

        payload = {
            "resume_id": resume_id,
            "candidate_email": email,
        }

        with patch(
            "app.api.v1.endpoints.applications.recalculate_application_match",
            return_value=None,
        ):
            res1 = client.post(
                f"/api/v1/jobs/{job_id}/applications",
                headers={"Authorization": f"Bearer {candidate_token}"},
                json=payload,
            )
            assert res1.status_code == 201

            res2 = client.post(
                f"/api/v1/jobs/{job_id}/applications",
                headers={"Authorization": f"Bearer {candidate_token}"},
                json=payload,
            )
            assert res2.status_code == 409
            assert "Ya existe una postulación" in res2.json()["detail"]


def test_max_applications_limit_fails():
    """Valida que un candidato no pueda realizar una cuarta postulación activa (límite de 3)."""
    with TestClient(app) as client:
        recruiter_token = get_auth_token_for_user(client, "recruiter@example.com")
        candidate_email = "candidate@example.com"
        candidate_token = get_auth_token_for_user(client, candidate_email)

        resume_id, job_id_1 = create_mock_resume_and_job(
            client, recruiter_token, candidate_email
        )

        future_deadline = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
        job_ids = [job_id_1]

        with patch(
            "app.api.v1.endpoints.jobs.generate_embedding", return_value=[0.1] * 384
        ):
            for i in range(3):
                job_res = client.post(
                    "/api/v1/jobs",
                    headers={"Authorization": f"Bearer {recruiter_token}"},
                    json={
                        "title": f"Backend Engineer {i+2}",
                        "area": "Tecnología",
                        "profile_type": "Senior",
                        "modality": "remoto",
                        "description": "Desarrollo de servicios web en FastAPI.",
                        "technical_skills": ["Python"],
                        "soft_skills": ["Comunicación"],
                        "status": "active",
                        "deadline": future_deadline,
                    },
                )
                job_ids.append(job_res.json()["id"])

        with patch(
            "app.api.v1.endpoints.applications.recalculate_application_match",
            return_value=None,
        ):
            for j_id in job_ids[:3]:
                res = client.post(
                    f"/api/v1/jobs/{j_id}/applications",
                    headers={"Authorization": f"Bearer {candidate_token}"},
                    json={"resume_id": resume_id, "candidate_email": candidate_email},
                )
                assert res.status_code == 201

            fourth_res = client.post(
                f"/api/v1/jobs/{job_ids[3]}/applications",
                headers={"Authorization": f"Bearer {candidate_token}"},
                json={"resume_id": resume_id, "candidate_email": candidate_email},
            )

            assert fourth_res.status_code == 400
            assert "límite máximo de 3 postulaciones" in fourth_res.json()["detail"]


def test_cancel_application_by_owner_success():
    """Valida que el candidato dueño de la postulación pueda cancelarla exitosamente (código 200)."""
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
            app_res = client.post(
                f"/api/v1/jobs/{job_id}/applications",
                headers={"Authorization": f"Bearer {candidate_token}"},
                json={"resume_id": resume_id, "candidate_email": candidate_email},
            )
        application_id = app_res.json()["id"]

        cancel_res = client.delete(
            f"/api/v1/applications/{application_id}",
            headers={"Authorization": f"Bearer {candidate_token}"},
        )

        assert cancel_res.status_code == 200
        assert cancel_res.json()["message"] == "Postulación cancelada con éxito"


def test_cancel_application_by_another_user_forbidden():
    """Valida que un usuario diferente no pueda cancelar una postulación ajena (código 403)."""
    with TestClient(app) as client:
        recruiter_token = get_auth_token_for_user(client, "recruiter@example.com")
        candidate_email = "owner@example.com"
        owner_token = get_auth_token_for_user(client, candidate_email)

        resume_id, job_id = create_mock_resume_and_job(
            client, recruiter_token, candidate_email
        )

        with patch(
            "app.api.v1.endpoints.applications.recalculate_application_match",
            return_value=None,
        ):
            app_res = client.post(
                f"/api/v1/jobs/{job_id}/applications",
                headers={"Authorization": f"Bearer {owner_token}"},
                json={"resume_id": resume_id, "candidate_email": candidate_email},
            )
        application_id = app_res.json()["id"]

        other_user_token = get_auth_token_for_user(client, "other@example.com")

        cancel_res = client.delete(
            f"/api/v1/applications/{application_id}",
            headers={"Authorization": f"Bearer {other_user_token}"},
        )

        assert cancel_res.status_code == 403
        assert (
            "No tienes permiso para cancelar esta postulación"
            in cancel_res.json()["detail"]
        )


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
        candidate_token = get_auth_token_for_user(client, candidate_email)
        resume_id, job_id = create_mock_resume_and_job(
            client, recruiter_token, candidate_email
        )

        with patch(
            "app.api.v1.endpoints.applications.recalculate_application_match",
            return_value=None,
        ):
            create_app_res = client.post(
                f"/api/v1/jobs/{job_id}/applications",
                headers={"Authorization": f"Bearer {candidate_token}"},
                json={"resume_id": resume_id, "candidate_email": candidate_email},
            )
        application_id = create_app_res.json()["id"]

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

        data = reject_res.json()
        assert data["candidate_email"] == candidate_email
        assert data["rejection_reason"] is not None
        assert "eliminada correctamente" in data["message"]


# =========================================================================
# PRUEBAS: MÁQUINA DE ESTADOS ESTRICTA, ROLES Y BLOQUEO DE VACANTES
# =========================================================================


def test_application_strict_state_machine_workflow():
    """Valida el ciclo de estados completo: received -> under_review -> interview_scheduled -> hired."""
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
            app_res = client.post(
                f"/api/v1/jobs/{job_id}/applications",
                headers={"Authorization": f"Bearer {candidate_token}"},
                json={"resume_id": resume_id, "candidate_email": candidate_email},
            )
        app_id = app_res.json()["id"]
        assert app_res.json()["status"] == "application_received"

        # 1. Pasar a review (view)
        view_res = client.patch(
            f"/api/v1/applications/{app_id}/view",
            headers={"Authorization": f"Bearer {recruiter_token}"},
        )
        assert view_res.status_code == 200
        assert view_res.json()["status"] == "application_under_review"

        # 2. Pasar a interview
        interview_res = client.patch(
            f"/api/v1/applications/{app_id}/interview",
            headers={"Authorization": f"Bearer {recruiter_token}"},
        )
        assert interview_res.status_code == 200
        assert interview_res.json()["status"] == "interview_scheduled"

        # 3. Contratar (hire) - Cierra la vacante automáticamente
        hire_res = client.patch(
            f"/api/v1/applications/{app_id}/hire",
            headers={"Authorization": f"Bearer {recruiter_token}"},
        )
        assert hire_res.status_code == 200
        assert hire_res.json()["status"] == "hired"


def test_invalid_state_transition_fails():
    """Valida que intentar saltarse estados (ej. pasar directo a interview desde received) devuelva 409 Conflict."""
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
            app_res = client.post(
                f"/api/v1/jobs/{job_id}/applications",
                headers={"Authorization": f"Bearer {candidate_token}"},
                json={"resume_id": resume_id, "candidate_email": candidate_email},
            )
        app_id = app_res.json()["id"]

        # Intentar programar entrevista estando en 'application_received' (debe fallar con 409)
        bad_transition = client.patch(
            f"/api/v1/applications/{app_id}/interview",
            headers={"Authorization": f"Bearer {recruiter_token}"},
        )
        assert bad_transition.status_code == 409
        assert (
            "debe encontrarse en estado 'application_under_review'"
            in bad_transition.json()["detail"]
        )


def test_unauthorized_role_changes_status_forbidden():
    """Valida que un usuario candidato no pueda alterar estados de postulaciones (403 Forbidden)."""
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
            app_res = client.post(
                f"/api/v1/jobs/{job_id}/applications",
                headers={"Authorization": f"Bearer {candidate_token}"},
                json={"resume_id": resume_id, "candidate_email": candidate_email},
            )
        app_id = app_res.json()["id"]

        # Candidato intenta marcar como visto (debe fallar con 403)
        res = client.patch(
            f"/api/v1/applications/{app_id}/view",
            headers={"Authorization": f"Bearer {candidate_token}"},
        )
        assert res.status_code == 403


def test_closed_job_blocks_application_modifications():
    """Valida que si la vacante está cerrada, cualquier cambio de estado o descarte arroje error 409."""
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
            app_res = client.post(
                f"/api/v1/jobs/{job_id}/applications",
                headers={"Authorization": f"Bearer {candidate_token}"},
                json={"resume_id": resume_id, "candidate_email": candidate_email},
            )
        app_id = app_res.json()["id"]

        # Cerrar la vacante explícitamente
        close_res = client.patch(
            f"/api/v1/jobs/{job_id}/close",
            headers={"Authorization": f"Bearer {recruiter_token}"},
        )
        assert close_res.status_code == 200

        # Intentar ver/marcar revisión con la vacante cerrada (debe dar 409)
        view_res = client.patch(
            f"/api/v1/applications/{app_id}/view",
            headers={"Authorization": f"Bearer {recruiter_token}"},
        )
        assert view_res.status_code == 409
        assert "vacante cerrada o archivada" in view_res.json()["detail"]

        # Intentar descartar con la vacante cerrada (debe dar 409)
        reject_res = client.patch(
            f"/api/v1/applications/{app_id}/reject",
            headers={"Authorization": f"Bearer {recruiter_token}"},
            json={"rejection_reason": "Fuera de tiempo"},
        )
        assert reject_res.status_code == 409
        assert "vacante cerrada o archivada" in reject_res.json()["detail"]


def test_hire_single_candidate_constraint():
    """Valida que no se pueda contratar a más de un candidato por vacante (409 Conflict)."""
    with TestClient(app) as client:
        recruiter_token = get_auth_token_for_user(client, "recruiter@example.com")

        # Candidato 1
        cand1_email = "cand1@example.com"
        cand1_token = get_auth_token_for_user(client, cand1_email)
        resume1_id, job_id = create_mock_resume_and_job(
            client, recruiter_token, cand1_email
        )

        # Candidato 2
        cand2_email = "cand2@example.com"
        cand2_token = get_auth_token_for_user(client, cand2_email)

        db = SessionLocal()
        try:
            from app.models.user import User
            from app.models.resume import Resume

            user2 = db.query(User).filter(User.email == cand2_email).first()
            resume2 = Resume(
                candidate_email=cand2_email,
                parsed_data={
                    "professional_title": "Dev",
                    "technical_skills": ["Python"],
                },
                user_id=user2.id if user2 else None,
            )
            db.add(resume2)
            db.commit()
            db.refresh(resume2)
            resume2_id = str(resume2.id)
        finally:
            db.close()

        # Postular candidato 1
        with patch(
            "app.api.v1.endpoints.applications.recalculate_application_match",
            return_value=None,
        ):
            res1 = client.post(
                f"/api/v1/jobs/{job_id}/applications",
                headers={"Authorization": f"Bearer {cand1_token}"},
                json={"resume_id": resume1_id, "candidate_email": cand1_email},
            )
            assert res1.status_code == 201
            app_id_1 = res1.json()["id"]

        # Postular candidato 2
        with patch(
            "app.api.v1.endpoints.applications.recalculate_application_match",
            return_value=None,
        ):
            res2 = client.post(
                f"/api/v1/jobs/{job_id}/applications",
                headers={"Authorization": f"Bearer {cand2_token}"},
                json={"resume_id": resume2_id, "candidate_email": cand2_email},
            )
            assert res2.status_code == 201
            app_id_2 = res2.json()["id"]

        # Contratar al candidato 1
        client.patch(
            f"/api/v1/applications/{app_id_1}/view",
            headers={"Authorization": f"Bearer {recruiter_token}"},
        )
        client.patch(
            f"/api/v1/applications/{app_id_1}/interview",
            headers={"Authorization": f"Bearer {recruiter_token}"},
        )
        hire_1 = client.patch(
            f"/api/v1/applications/{app_id_1}/hire",
            headers={"Authorization": f"Bearer {recruiter_token}"},
        )
        assert hire_1.status_code == 200, hire_1.text

        # Intentar interactuar con el candidato 2 (la vacante se cerró al contratar al 1, debe arrojar 409)
        view_2 = client.patch(
            f"/api/v1/applications/{app_id_2}/view",
            headers={"Authorization": f"Bearer {recruiter_token}"},
        )
        assert view_2.status_code == 409
        assert "vacante cerrada o archivada" in view_2.json()["detail"]


def test_hire_same_candidate_twice_fails():
    """Valida que intentar contratar a un candidato que ya fue contratado o reintentar el endpoint de contratación devuelva un error 409 Conflict."""
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
            app_res = client.post(
                f"/api/v1/jobs/{job_id}/applications",
                headers={"Authorization": f"Bearer {candidate_token}"},
                json={"resume_id": resume_id, "candidate_email": candidate_email},
            )
        app_id = app_res.json()["id"]

        # 1. Llevar la postulación por el flujo estricto hasta 'hired'
        client.patch(
            f"/api/v1/applications/{app_id}/view",
            headers={"Authorization": f"Bearer {recruiter_token}"},
        )
        client.patch(
            f"/api/v1/applications/{app_id}/interview",
            headers={"Authorization": f"Bearer {recruiter_token}"},
        )
        first_hire = client.patch(
            f"/api/v1/applications/{app_id}/hire",
            headers={"Authorization": f"Bearer {recruiter_token}"},
        )
        assert first_hire.status_code == 200
        assert first_hire.json()["status"] == "hired"

        # 2. Intentar contratar al mismo candidato por segunda vez (o con la vacante ya cerrada)
        second_hire = client.patch(
            f"/api/v1/applications/{app_id}/hire",
            headers={"Authorization": f"Bearer {recruiter_token}"},
        )

        # Debe fallar con 409 Conflict (ya sea por restricción de estado o por estar la vacante cerrada/archivada)
        assert second_hire.status_code == 409


def test_hire_application_queues_emails_for_all_candidates():
    """Valida que al contratar a un candidato, se encoluen y disparen los correos tanto para el candidato contratado como para los demás postulantes de la vacante."""
    with TestClient(app) as client:
        recruiter_token = get_auth_token_for_user(client, "recruiter@example.com")

        # Candidato 1 (El que será contratado)
        cand1_email = "cand1@example.com"
        cand1_token = get_auth_token_for_user(client, cand1_email)
        resume1_id, job_id = create_mock_resume_and_job(
            client, recruiter_token, cand1_email
        )

        # Candidato 2 (El que recibirá el correo de vacante cerrada)
        cand2_email = "cand2@example.com"
        cand2_token = get_auth_token_for_user(client, cand2_email)

        db = SessionLocal()
        try:
            from app.models.user import User
            from app.models.resume import Resume

            user2 = db.query(User).filter(User.email == cand2_email).first()
            resume2 = Resume(
                candidate_email=cand2_email,
                parsed_data={
                    "professional_title": "Dev",
                    "technical_skills": ["Python"],
                },
                user_id=user2.id if user2 else None,
            )
            db.add(resume2)
            db.commit()
            db.refresh(resume2)
            resume2_id = str(resume2.id)
        finally:
            db.close()

        # Postular candidato 1
        with patch(
            "app.api.v1.endpoints.applications.recalculate_application_match",
            return_value=None,
        ):
            res1 = client.post(
                f"/api/v1/jobs/{job_id}/applications",
                headers={"Authorization": f"Bearer {cand1_token}"},
                json={"resume_id": resume1_id, "candidate_email": cand1_email},
            )
            assert res1.status_code == 201
            app_id_1 = res1.json()["id"]

        # Postular candidato 2
        with patch(
            "app.api.v1.endpoints.applications.recalculate_application_match",
            return_value=None,
        ):
            res2 = client.post(
                f"/api/v1/jobs/{job_id}/applications",
                headers={"Authorization": f"Bearer {cand2_token}"},
                json={"resume_id": resume2_id, "candidate_email": cand2_email},
            )
            assert res2.status_code == 201

        # Llevar al candidato 1 al estado 'interview_scheduled'
        client.patch(
            f"/api/v1/applications/{app_id_1}/view",
            headers={"Authorization": f"Bearer {recruiter_token}"},
        )
        client.patch(
            f"/api/v1/applications/{app_id_1}/interview",
            headers={"Authorization": f"Bearer {recruiter_token}"},
        )

        # Parchear send_email para capturar los correos encolados
        sent_emails = []

        def mock_send_email(to_email, subject, body_text):
            sent_emails.append({"to": to_email, "subject": subject, "body": body_text})
            return True

        with patch(
            "app.api.v1.endpoints.applications.send_email", side_effect=mock_send_email
        ):
            # Contratar al candidato 1 (esto dispara el cierre de vacante y notificación a ambos)
            hire_res = client.patch(
                f"/api/v1/applications/{app_id_1}/hire",
                headers={"Authorization": f"Bearer {recruiter_token}"},
            )
            assert hire_res.status_code == 200, hire_res.text

        # Como TestClient ejecuta BackgroundTasks, verificamos los correos capturados
        # (Si TestClient no los ejecuta automáticamente según la versión, puedes forzar el consumo de la cola de app si aplica,
        # pero con el patch directo a send_email ejecutado por TestClient al finalizar la petición, bastará).

        recipients = [email["to"] for email in sent_emails]

        # Comprobamos que se hayan encolado/enviado los dos correos (cand1 y cand2)
        assert len(sent_emails) == 2
        assert cand1_email in recipients
        assert cand2_email in recipients
