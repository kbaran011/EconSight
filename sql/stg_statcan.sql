CREATE OR REPLACE VIEW staging.stg_statcan_observations AS
SELECT
    id,
    indicator_key,
    reference_date,
    value,
    status,
    ingested_at,
    pipeline_run_id,
    to_char(reference_date, 'YYYY-MM')          AS period_label,
    status IN ('A', 'P')                         AS is_reliable
FROM raw.statcan_observations;
