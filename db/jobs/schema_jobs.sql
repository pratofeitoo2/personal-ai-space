-- jobs.db: Job application tracking — companies, applications, interviews, contacts
--
-- Schema design:
--   companies      → organizations you're engaging with
--   applications   → job applications (position-level tracking)
--   interviews     → interview rounds per application
--   contacts       → people you know at companies
--
-- This follows the same pattern as tasks/calendar/self etc.
-- and integrates with db_manager.py for connection pooling, WAL mode, etc.

CREATE TABLE IF NOT EXISTS companies (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    website TEXT,
    industry TEXT,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS applications (
    id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    job_title TEXT NOT NULL,
    job_url TEXT,
    job_description TEXT,
    salary_range TEXT,
    location TEXT,
    remote BOOLEAN DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'saved'
        CHECK(status IN ('saved','applied','screening','interview','offer','rejected','withdrawn','accepted')),
    applied_date DATE,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS interviews (
    id TEXT PRIMARY KEY,
    application_id TEXT NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    round_number INTEGER NOT NULL DEFAULT 1,
    interview_type TEXT NOT NULL DEFAULT 'phone'
        CHECK(interview_type IN ('phone','video','technical','onsite','case','panel','take_home','cultural','other')),
    scheduled_at DATETIME,
    duration_minutes INTEGER,
    interviewer_name TEXT,
    interviewer_role TEXT,
    feedback TEXT,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS contacts (
    id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    role TEXT,
    email TEXT,
    linkedin TEXT,
    phone TEXT,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ── Indexes ────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_applications_company   ON applications(company_id);
CREATE INDEX IF NOT EXISTS idx_applications_status    ON applications(status);
CREATE INDEX IF NOT EXISTS idx_applications_applied   ON applications(applied_date);
CREATE INDEX IF NOT EXISTS idx_interviews_application  ON interviews(application_id);
CREATE INDEX IF NOT EXISTS idx_interviews_scheduled   ON interviews(scheduled_at);
CREATE INDEX IF NOT EXISTS idx_contacts_company        ON contacts(company_id);
