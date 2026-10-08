-- =============================================================================
-- ESQUEMA BASE DE PluriJob
-- PostgreSQL 16 + pgvector
--
-- Este script crea el modelo mínimo necesario para cumplir con MVP.md y con la
-- estructura de ORM actual del backend en app/models.
-- =============================================================================

-- 1. EXTENSIONES
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. LIMPIEZA DE INSTANCIA PREVIA (para recrear desde cero)
DROP TRIGGER IF EXISTS trg_cleanup_expired_casual_data ON resumes;
DROP TRIGGER IF EXISTS trg_link_user_on_signup ON users;
DROP TRIGGER IF EXISTS trg_validate_application_candidate ON applications;
DROP TRIGGER IF EXISTS trg_email_templates_updated_at ON email_templates;
DROP TRIGGER IF EXISTS trg_applications_updated_at ON applications;
DROP TRIGGER IF EXISTS trg_jobs_updated_at ON jobs;
DROP TRIGGER IF EXISTS trg_resumes_updated_at ON resumes;
DROP TRIGGER IF EXISTS trg_users_updated_at ON users;

DROP TABLE IF EXISTS email_templates CASCADE;
DROP TABLE IF EXISTS applications CASCADE;
DROP TABLE IF EXISTS jobs CASCADE;
DROP TABLE IF EXISTS resumes CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS skills_cache CASCADE;

DROP TYPE IF EXISTS application_status_enum CASCADE;
DROP TYPE IF EXISTS job_status_enum CASCADE;
DROP TYPE IF EXISTS job_modality_enum CASCADE;
DROP TYPE IF EXISTS user_role_enum CASCADE;

-- 3. ENUMS
CREATE TYPE user_role_enum AS ENUM ('casual', 'registered', 'recruiter', 'admin');
CREATE TYPE job_modality_enum AS ENUM ('presencial', 'remoto', 'hibrido');
CREATE TYPE job_status_enum AS ENUM ('draft', 'active', 'expired', 'closed');
CREATE TYPE application_status_enum AS ENUM (
    'received',
    'under_review',
    'shortlisted',
    'interview_scheduled',
    'rejected',
    'hired'
);

-- 4. USUARIOS
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255),
    full_name VARCHAR(150),
    role user_role_enum NOT NULL DEFAULT 'casual',
    google_id VARCHAR(255) UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX uq_users_email_lower ON users (LOWER(email));
CREATE INDEX idx_users_role ON users (role);
CREATE INDEX idx_users_created_at ON users (created_at DESC);

-- 5. CVs
CREATE TABLE resumes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    candidate_email VARCHAR(255) NOT NULL,
    raw_text TEXT,
    parsed_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    extracted_skills JSONB NOT NULL DEFAULT '[]'::jsonb,
    embedding vector(384),
    file_name VARCHAR(255),
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX uq_resumes_candidate_email_lower ON resumes (LOWER(candidate_email));
CREATE UNIQUE INDEX uq_resumes_user_id ON resumes (user_id) WHERE user_id IS NOT NULL;
CREATE INDEX idx_resumes_updated_at ON resumes (updated_at DESC);
CREATE INDEX idx_resumes_expires_at ON resumes (expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX idx_resumes_embedding_hnsw ON resumes USING hnsw (embedding vector_cosine_ops);

-- 6. VACANTES
CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recruiter_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    title VARCHAR(150) NOT NULL,
    area VARCHAR(100) NOT NULL,
    profile_type TEXT NOT NULL,
    modality job_modality_enum NOT NULL DEFAULT 'presencial',
    location VARCHAR(150),
    description TEXT NOT NULL,
    technical_skills JSONB NOT NULL DEFAULT '[]'::jsonb,
    soft_skills JSONB NOT NULL DEFAULT '[]'::jsonb,
    embedding vector(384),
    status job_status_enum NOT NULL DEFAULT 'draft',
    deadline TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    benefits TEXT,
    CONSTRAINT chk_jobs_deadline_after_creation
        CHECK (deadline IS NULL OR deadline > created_at),
    CONSTRAINT chk_jobs_location_by_modality
        CHECK (modality = 'remoto' OR NULLIF(BTRIM(location), '') IS NOT NULL)
);

CREATE INDEX idx_jobs_recruiter ON jobs (recruiter_id);
CREATE INDEX idx_jobs_status ON jobs (status);
CREATE INDEX idx_jobs_area_modality ON jobs (area, modality);
CREATE INDEX idx_jobs_deadline ON jobs (deadline);
CREATE INDEX idx_jobs_created_at ON jobs (created_at DESC);
CREATE INDEX idx_jobs_embedding_hnsw ON jobs USING hnsw (embedding vector_cosine_ops);

-- 7. POSTULACIONES
CREATE TABLE applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    resume_id UUID NOT NULL REFERENCES resumes(id) ON DELETE RESTRICT,
    candidate_email VARCHAR(255) NOT NULL,
    match_score NUMERIC(5,2),
    match_details JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_overqualified BOOLEAN NOT NULL DEFAULT FALSE,
    ai_analysis JSONB NOT NULL DEFAULT '{}'::jsonb,
    status application_status_enum NOT NULL DEFAULT 'received',
    rejection_reason TEXT,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_applications_match_score
        CHECK (match_score IS NULL OR (match_score >= 0 AND match_score <= 100))
);

CREATE UNIQUE INDEX uq_applications_job_candidate_lower ON applications (job_id, LOWER(candidate_email));
CREATE INDEX idx_applications_job_score ON applications (job_id, match_score DESC NULLS LAST);
CREATE INDEX idx_applications_user ON applications (user_id);
CREATE INDEX idx_applications_candidate_email ON applications (candidate_email);
CREATE INDEX idx_applications_overqualified ON applications (is_overqualified) WHERE is_overqualified = TRUE;
CREATE INDEX idx_applications_user_applied_at ON applications (user_id, applied_at DESC);
CREATE INDEX idx_applications_job_status ON applications (job_id, status);

-- 8. CACHE DE HABILIDADES
CREATE TABLE skills_cache (
    id BIGSERIAL PRIMARY KEY,
    raw_term VARCHAR(150) NOT NULL,
    normalized_term VARCHAR(150) NOT NULL,
    esco_uri VARCHAR(255),
    embedding vector(384),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX uq_skills_cache_raw_term_lower ON skills_cache (LOWER(raw_term));
CREATE INDEX idx_skills_cache_normalized_term ON skills_cache (normalized_term);
CREATE INDEX idx_skills_cache_embedding_hnsw ON skills_cache USING hnsw (embedding vector_cosine_ops);

-- 9. PLANTILLAS DE CORREO
CREATE TABLE email_templates (
    id BIGSERIAL PRIMARY KEY,
    template_key VARCHAR(50) UNIQUE NOT NULL,
    subject VARCHAR(200) NOT NULL,
    body_text TEXT NOT NULL,
    is_system_fallback BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE OR REPLACE FUNCTION cleanup_expired_casual_data()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    DELETE FROM applications a
    USING resumes r
    WHERE a.resume_id = r.id
      AND r.user_id IS NULL
      AND r.expires_at IS NOT NULL
      AND r.expires_at <= NOW();

    DELETE FROM resumes r
    WHERE r.user_id IS NULL
      AND r.expires_at IS NOT NULL
      AND r.expires_at <= NOW();

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_cleanup_expired_casual_data
AFTER INSERT OR UPDATE OF expires_at ON resumes
FOR EACH ROW EXECUTE FUNCTION cleanup_expired_casual_data();

-- 10. FUNCIÓN PARA updated_at
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_resumes_updated_at
BEFORE UPDATE ON resumes
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_jobs_updated_at
BEFORE UPDATE ON jobs
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_applications_updated_at
BEFORE UPDATE ON applications
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_email_templates_updated_at
BEFORE UPDATE ON email_templates
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- 11. VALIDACIÓN DE CANDIDATOS EN APLICACIONES
CREATE OR REPLACE FUNCTION validate_application_candidate()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    resume_user_id UUID;
    resume_candidate_email VARCHAR(255);
BEGIN
    SELECT r.user_id, r.candidate_email
    INTO resume_user_id, resume_candidate_email
    FROM resumes r
    WHERE r.id = NEW.resume_id;

    IF resume_candidate_email IS NULL THEN
        RAISE EXCEPTION 'El CV % no existe o no tiene candidate_email asignado', NEW.resume_id;
    END IF;

    IF LOWER(COALESCE(NEW.candidate_email, '')) <> LOWER(COALESCE(resume_candidate_email, '')) THEN
        RAISE EXCEPTION 'candidate_email no coincide con el correo registrado en el CV';
    END IF;

    IF NEW.user_id IS NOT NULL AND resume_user_id IS NOT NULL AND NEW.user_id <> resume_user_id THEN
        RAISE EXCEPTION 'El user_id de la postulación no coincide con el propietario registrado del CV';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validate_application_candidate
BEFORE INSERT OR UPDATE OF user_id, resume_id, candidate_email ON applications
FOR EACH ROW EXECUTE FUNCTION validate_application_candidate();

-- 12. VINCULACIÓN AUTOMÁTICA AL REGISTRARSE
CREATE OR REPLACE FUNCTION link_resumes_and_applications_on_user_signup()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE resumes
    SET user_id = NEW.id
    WHERE LOWER(candidate_email) = LOWER(NEW.email)
      AND user_id IS NULL;

    UPDATE applications
    SET user_id = NEW.id
    WHERE LOWER(candidate_email) = LOWER(NEW.email)
      AND user_id IS NULL;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_link_user_on_signup
AFTER INSERT ON users
FOR EACH ROW EXECUTE FUNCTION link_resumes_and_applications_on_user_signup();

-- 13. SEMILLAS BÁSICAS
INSERT INTO skills_cache (raw_term, normalized_term, esco_uri)
VALUES
    ('trabajo en equipo', 'trabajo en equipo', NULL),
    ('comunicación', 'comunicación', NULL),
    ('resolución de problemas', 'resolución de problemas', NULL),
    ('adaptabilidad', 'adaptabilidad', NULL),
    ('empatía', 'empatía', NULL),
    ('pensamiento crítico', 'pensamiento crítico', NULL),
    ('liderazgo', 'liderazgo', NULL),
    ('aprendizaje continuo', 'aprendizaje continuo', NULL),
    ('creatividad', 'creatividad', NULL),
    ('organización', 'organización', NULL),
    ('proactividad', 'proactividad', NULL),
    ('negociación', 'negociación', NULL)
ON CONFLICT DO NOTHING;

INSERT INTO email_templates (template_key, subject, body_text, is_system_fallback)
VALUES
    (
        'account_created',
        'Bienvenido a PluriJob',
        'Hola {{candidate_name}}, ¡te damos la bienvenida a PluriJob! Ya puedes completar tu perfil, subir tu CV y postular a las vacantes que te interesen.',
        TRUE
    ),
    (
        'application_received',
        'Tu postulación fue recibida',
        'Hola {{candidate_name}}, hemos recibido tu postulación para {{job_title}}. En breve revisaremos tu perfil y te contactaremos si avanzas en el proceso.',
        TRUE
    ),
    (
        'application_rejected',
        'Actualización de tu postulación',
        'Hola {{candidate_name}}, gracias por tu interés. Después de revisar tu perfil, en esta ocasión no continuaremos con tu postulación para {{job_title}}.',
        TRUE
    ),
    (
        'vacancy_closed',
        'Vacante cerrada',
        'Hola {{candidate_name}}, la vacante {{job_title}} ha sido cerrada por el reclutador. Gracias por tu interés y te invitamos a seguir revisando nuevas oportunidades.',
        TRUE
    ),
    (
        'interview_progress',
        'Avance de tu proceso',
        'Hola {{candidate_name}}, hemos avanzado en tu proceso para {{job_title}}. Te contactaremos para coordinar la siguiente etapa o entrevista.',
        TRUE
    ),
    (
        'hired',
        '¡Felicidades! Has sido seleccionado',
        'Hola {{candidate_name}}, queremos informarte que has avanzado de forma favorable en el proceso de {{job_title}} y hemos decidido continuar contigo.',
        TRUE
    ),
    (
        'status_update',
        'Actualización de tu postulación',
        'Hola, hay una actualización en el estado de tu postulación. Te informaremos los próximos pasos.',
        TRUE
    )
ON CONFLICT (template_key) DO NOTHING;

-- 14. COMENTARIOS
COMMENT ON COLUMN resumes.embedding IS 'Vector pgvector de 384 dimensiones para matching semántico';
COMMENT ON COLUMN jobs.embedding IS 'Vector pgvector de 384 dimensiones para matching semántico';
COMMENT ON COLUMN skills_cache.embedding IS 'Vector pgvector de 384 dimensiones para normalización y matching';


ALTER TABLE skills_cache ADD CONSTRAINT uq_skills_cache_esco_uri UNIQUE (esco_uri);

-- Crear índice HNSW para distancia de coseno
CREATE INDEX IF NOT EXISTS idx_skills_cache_embedding_hnsw 
ON skills_cache 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

ALTER TABLE jobs ALTER COLUMN profile_type TYPE TEXT;