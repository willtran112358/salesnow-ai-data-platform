-- SalesNow AI Data Platform — Aurora PostgreSQL schema (serving layer)
-- Migration: 001_initial_schema.sql

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

CREATE TABLE IF NOT EXISTS companies (
    company_id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    corporate_number    VARCHAR(13) UNIQUE,
    company_name        VARCHAR(500) NOT NULL,
    company_name_normalized VARCHAR(500),
    prefecture_code     CHAR(2),
    address             TEXT,
    postal_code         VARCHAR(8),
    industry_code       VARCHAR(10),
    employee_count      INTEGER,
    capital_amount      BIGINT,
    listing_status      VARCHAR(20),
    founded_date        DATE,
    website_url         VARCHAR(500),
    salesforce_account_id VARCHAR(18),
    hubspot_company_id  VARCHAR(50),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_companies_name_trgm ON companies USING gin (company_name gin_trgm_ops);
CREATE INDEX idx_companies_prefecture ON companies (prefecture_code);
CREATE INDEX idx_companies_employee_count ON companies (employee_count);
CREATE INDEX idx_companies_sf_id ON companies (salesforce_account_id) WHERE salesforce_account_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS activities (
    activity_id     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(company_id),
    activity_type   VARCHAR(50) NOT NULL,
    activity_date   TIMESTAMPTZ NOT NULL,
    title           TEXT,
    source_url      VARCHAR(1000),
    signal_strength FLOAT DEFAULT 0.0,
    raw_payload     JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_activities_company_date ON activities (company_id, activity_date DESC);
CREATE INDEX idx_activities_type ON activities (activity_type);

CREATE TABLE IF NOT EXISTS intent_scores (
    company_id       UUID NOT NULL REFERENCES companies(company_id),
    score_date       DATE NOT NULL,
    hiring_intent    FLOAT,
    growth_intent    FLOAT,
    funding_intent   FLOAT,
    composite_score  FLOAT,
    model_version    VARCHAR(20),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (company_id, score_date)
);

CREATE TABLE IF NOT EXISTS ai_summaries (
    company_id    UUID PRIMARY KEY REFERENCES companies(company_id),
    summary_text  TEXT NOT NULL,
    source_hash   VARCHAR(64),
    model_version VARCHAR(20),
    generated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at    TIMESTAMPTZ
);

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_companies_updated_at
    BEFORE UPDATE ON companies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
