CREATE OR REPLACE VIEW staging.stg_boc_observations AS
SELECT
    id,
    series_key,
    reference_date,
    value,
    ingested_at,
    pipeline_run_id,
    to_char(reference_date, 'YYYY-MM')          AS period_label,
    true                                         AS is_month_end
FROM raw.boc_observations;
