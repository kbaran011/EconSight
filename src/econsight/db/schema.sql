-- Schemas
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS marts;
CREATE SCHEMA IF NOT EXISTS meta;

-- raw.statcan_observations
CREATE TABLE IF NOT EXISTS raw.statcan_observations (
    id              bigserial   PRIMARY KEY,
    indicator_key   text        NOT NULL,
    reference_date  date        NOT NULL,
    value           numeric     NOT NULL,
    status          char(1)     NOT NULL CHECK (status IN ('A', 'P')),
    ingested_at     timestamptz NOT NULL DEFAULT now(),
    pipeline_run_id uuid,
    UNIQUE (indicator_key, reference_date)
);

-- raw.boc_observations
CREATE TABLE IF NOT EXISTS raw.boc_observations (
    id              bigserial   PRIMARY KEY,
    series_key      text        NOT NULL,
    reference_date  date        NOT NULL,
    value           numeric     NOT NULL,
    ingested_at     timestamptz NOT NULL DEFAULT now(),
    pipeline_run_id uuid,
    UNIQUE (series_key, reference_date)
);

-- meta.pipeline_runs
CREATE TABLE IF NOT EXISTS meta.pipeline_runs (
    id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    started_at   timestamptz NOT NULL DEFAULT now(),
    finished_at  timestamptz,
    status       text        CHECK (status IN ('running', 'success', 'failed')),
    rows_loaded  int,
    error_msg    text
);

-- marts.mart_monthly_macro_indicators
CREATE TABLE IF NOT EXISTS marts.mart_monthly_macro_indicators (
    period_date         date        NOT NULL,
    period_label        text        NOT NULL,
    gdp                 numeric,
    cpi                 numeric,
    unemployment_rate   numeric,
    ippi                numeric,
    retail_trade        numeric,
    overnight_rate      numeric,
    cadusd              numeric,
    bond_10yr           numeric,
    m2pp                numeric,
    cpi_yoy             numeric,
    yield_spread        numeric,
    unemployment_delta  numeric,
    updated_at          timestamptz NOT NULL DEFAULT now(),
    data_complete       boolean GENERATED ALWAYS AS (
                            cpi IS NOT NULL AND unemployment_rate IS NOT NULL
                            AND overnight_rate IS NOT NULL AND bond_10yr IS NOT NULL
                            AND gdp IS NOT NULL
                        ) STORED,
    UNIQUE (period_date)
);

-- marts.model_forecasts
CREATE TABLE IF NOT EXISTS marts.model_forecasts (
    id                bigserial   PRIMARY KEY,
    period_date       date        NOT NULL,
    target            text        NOT NULL,
    horizon_months    int         NOT NULL,
    model_type        text        NOT NULL,
    point_forecast    numeric     NOT NULL,
    p10               numeric,
    p50               numeric,
    p90               numeric,
    scenario_base     numeric,
    scenario_upside   numeric,
    scenario_downside numeric,
    created_at        timestamptz NOT NULL DEFAULT now(),
    UNIQUE (period_date, target, horizon_months, model_type)
);

-- marts.economic_health_score
CREATE TABLE IF NOT EXISTS marts.economic_health_score (
    period_date      date        PRIMARY KEY,
    score            numeric     NOT NULL,
    component_scores jsonb       NOT NULL,
    updated_at       timestamptz NOT NULL DEFAULT now()
);

-- Read-only role for API endpoints (safe to re-run)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'econsight_reader') THEN
        CREATE ROLE econsight_reader LOGIN PASSWORD 'kbdbaran';
    END IF;
END$$;
GRANT USAGE ON SCHEMA marts TO econsight_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA marts TO econsight_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA marts GRANT SELECT ON TABLES TO econsight_reader;
