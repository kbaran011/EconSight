CREATE OR REPLACE VIEW staging.stg_statcan_observations AS
SELECT * FROM raw.statcan_observations WHERE false;
