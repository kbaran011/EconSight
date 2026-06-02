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
