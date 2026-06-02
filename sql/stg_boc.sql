CREATE OR REPLACE VIEW staging.stg_boc_observations AS
SELECT * FROM raw.boc_observations WHERE false;
