-- =============================================================================
-- ESQUEMA DE BASE DE DATOS: PluriJob
-- PostgreSQL + pgvector
--
-- Modelo de embeddings recomendado:
-- sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
-- Dimension: 384
-- Motivo: buen soporte multilingue, incluido espanol, para matching semantico.
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;

DO $$
BEGIN
	CREATE TYPE user_role_enum AS ENUM ('casual', 'registered', 'recruiter', 'admin');
EXCEPTION
	WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
	CREATE TYPE job_modality_enum AS ENUM ('presencial', 'remoto', 'hibrido');
EXCEPTION
	WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
	CREATE TYPE job_status_enum AS ENUM ('draft', 'active', 'closed');
EXCEPTION
	WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
	CREATE TYPE application_status_enum AS ENUM (
		'received',
		'under_review',
		'shortlisted',
		'interview_scheduled',
		'rejected',
		'hired'
	);
EXCEPTION
	WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS users (
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

CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS uq_users_email_lower ON users(LOWER(email));

CREATE TABLE IF NOT EXISTS resumes (
	id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
	user_id UUID REFERENCES users(id) ON DELETE SET NULL,
	candidate_email VARCHAR(255) NOT NULL,
	raw_text TEXT,
	parsed_data JSONB NOT NULL DEFAULT '{}'::jsonb,
	extracted_skills JSONB NOT NULL DEFAULT '[]'::jsonb,
	embedding vector(384),
	file_name VARCHAR(255),
	created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_resumes_candidate_email_lower
ON resumes(LOWER(candidate_email));

CREATE UNIQUE INDEX IF NOT EXISTS uq_resumes_user_id
ON resumes(user_id)
WHERE user_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_resumes_embedding_hnsw
ON resumes USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_resumes_updated_at ON resumes(updated_at DESC);

CREATE TABLE IF NOT EXISTS jobs (
	id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
	recruiter_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
	title VARCHAR(150) NOT NULL,
	area VARCHAR(100) NOT NULL,
	profile_type VARCHAR(100) NOT NULL,
	modality job_modality_enum NOT NULL DEFAULT 'presencial',
	location VARCHAR(150),
	description TEXT NOT NULL,
	required_skills JSONB NOT NULL DEFAULT '[]'::jsonb,
	optional_skills JSONB NOT NULL DEFAULT '[]'::jsonb,
	embedding vector(384),
	status job_status_enum NOT NULL DEFAULT 'draft',
	deadline TIMESTAMPTZ,
	created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
	CONSTRAINT chk_jobs_deadline_after_creation
		CHECK (deadline IS NULL OR deadline > created_at),
	CONSTRAINT chk_jobs_location_by_modality
		CHECK (modality = 'remoto' OR NULLIF(BTRIM(location), '') IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_jobs_recruiter ON jobs(recruiter_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_area_modality ON jobs(area, modality);
CREATE INDEX IF NOT EXISTS idx_jobs_deadline ON jobs(deadline);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_embedding_hnsw
ON jobs USING hnsw (embedding vector_cosine_ops);

CREATE TABLE IF NOT EXISTS applications (
	id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
	job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
	user_id UUID REFERENCES users(id) ON DELETE SET NULL,
	resume_id UUID NOT NULL REFERENCES resumes(id) ON DELETE RESTRICT,
	candidate_email VARCHAR(255) NOT NULL,
	match_score NUMERIC(5, 2),
	is_overqualified BOOLEAN NOT NULL DEFAULT FALSE,
	ai_analysis JSONB NOT NULL DEFAULT '{}'::jsonb,
	status application_status_enum NOT NULL DEFAULT 'received',
	rejection_reason TEXT,
	applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
	CONSTRAINT chk_applications_match_score
		CHECK (match_score IS NULL OR (match_score >= 0 AND match_score <= 100))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_applications_job_candidate_lower
ON applications(job_id, LOWER(candidate_email));

CREATE INDEX IF NOT EXISTS idx_applications_job_score
ON applications(job_id, match_score DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_applications_user ON applications(user_id);
CREATE INDEX IF NOT EXISTS idx_applications_candidate_email ON applications(candidate_email);
CREATE INDEX IF NOT EXISTS idx_applications_overqualified
ON applications(is_overqualified)
WHERE is_overqualified = TRUE;

CREATE TABLE IF NOT EXISTS skills_cache (
	id BIGSERIAL PRIMARY KEY,
	raw_term VARCHAR(150) NOT NULL,
	normalized_term VARCHAR(150) NOT NULL,
	esco_uri VARCHAR(255),
	embedding vector(384),
	created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_skills_cache_raw_term_lower
ON skills_cache(LOWER(raw_term));

CREATE INDEX IF NOT EXISTS idx_skills_cache_normalized_term
ON skills_cache(normalized_term);
CREATE INDEX IF NOT EXISTS idx_skills_cache_embedding_hnsw
ON skills_cache USING hnsw (embedding vector_cosine_ops);

CREATE TABLE IF NOT EXISTS email_templates (
	id BIGSERIAL PRIMARY KEY,
	template_key VARCHAR(50) UNIQUE NOT NULL,
	subject VARCHAR(200) NOT NULL,
	body_text TEXT NOT NULL,
	is_system_fallback BOOLEAN NOT NULL DEFAULT FALSE,
	created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
	NEW.updated_at = CURRENT_TIMESTAMP;
	RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_users_updated_at ON users;
CREATE TRIGGER trg_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_resumes_updated_at ON resumes;
CREATE TRIGGER trg_resumes_updated_at
BEFORE UPDATE ON resumes
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_jobs_updated_at ON jobs;
CREATE TRIGGER trg_jobs_updated_at
BEFORE UPDATE ON jobs
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_applications_updated_at ON applications;
CREATE TRIGGER trg_applications_updated_at
BEFORE UPDATE ON applications
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_email_templates_updated_at ON email_templates;
CREATE TRIGGER trg_email_templates_updated_at
BEFORE UPDATE ON email_templates
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

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
		RAISE EXCEPTION 'El CV % no tiene candidate_email', NEW.resume_id;
	END IF;

	IF LOWER(NEW.candidate_email::TEXT) <> LOWER(resume_candidate_email::TEXT) THEN
		RAISE EXCEPTION 'candidate_email no coincide con el correo del CV';
	END IF;

	IF NEW.user_id IS DISTINCT FROM resume_user_id THEN
		RAISE EXCEPTION 'user_id no coincide con el propietario del CV';
	END IF;

	RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_validate_application_candidate ON applications;
CREATE TRIGGER trg_validate_application_candidate
BEFORE INSERT OR UPDATE OF user_id, resume_id, candidate_email ON applications
FOR EACH ROW EXECUTE FUNCTION validate_application_candidate();

COMMENT ON COLUMN resumes.embedding IS
'384 dimensiones: paraphrase-multilingual-MiniLM-L12-v2';
COMMENT ON COLUMN jobs.embedding IS
'384 dimensiones: paraphrase-multilingual-MiniLM-L12-v2';
COMMENT ON COLUMN skills_cache.embedding IS
'384 dimensiones: paraphrase-multilingual-MiniLM-L12-v2';

-- Alteraciones incrementales del esquema:
-- 2026-09-23: se agregan expires_at para CVs casuales y match_details
-- para soportar expiración y detalle explicable del matching.
ALTER TABLE resumes
ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_resumes_expires_at
ON resumes(expires_at)
WHERE expires_at IS NOT NULL;

ALTER TABLE applications
ADD COLUMN IF NOT EXISTS match_details JSONB NOT NULL DEFAULT '{}'::jsonb;

-- 2026-09-24: se sincroniza applications con el modelo ORM para
-- registrar sobrecalificación y análisis generado por IA.
ALTER TABLE applications
ADD COLUMN IF NOT EXISTS is_overqualified BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE applications
ADD COLUMN IF NOT EXISTS ai_analysis JSONB NOT NULL DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_applications_user_applied_at
ON applications(user_id, applied_at DESC);

CREATE INDEX IF NOT EXISTS idx_applications_job_status
ON applications(job_id, status);
----