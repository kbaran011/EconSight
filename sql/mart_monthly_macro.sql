INSERT INTO marts.mart_monthly_macro_indicators (
    period_date, period_label,
    gdp, cpi, unemployment_rate, ippi, retail_trade,
    overnight_rate, cadusd, bond_10yr, m2pp,
    cpi_yoy, yield_spread, unemployment_delta,
    updated_at
)
WITH monthly_statcan AS (
    SELECT
        date_trunc('month', reference_date)::date                                AS period_date,
        MAX(CASE WHEN indicator_key = '36-10-0104-01' THEN value END)            AS gdp,
        MAX(CASE WHEN indicator_key = '18-10-0004-01' THEN value END)            AS cpi,
        MAX(CASE WHEN indicator_key = '14-10-0287-01' THEN value END)            AS unemployment_rate,
        MAX(CASE WHEN indicator_key = '18-10-0266-01' THEN value END)            AS ippi,
        MAX(CASE WHEN indicator_key = '20-10-0008-01' THEN value END)            AS retail_trade
    FROM raw.statcan_observations
    GROUP BY 1
),
monthly_boc AS (
    SELECT
        date_trunc('month', reference_date)::date                                AS period_date,
        MAX(CASE WHEN series_key = 'V39079'    THEN value END)                   AS overnight_rate,
        MAX(CASE WHEN series_key = 'FXCADUSD'  THEN value END)                   AS cadusd,
        MAX(CASE WHEN series_key = 'V122487'   THEN value END)                   AS bond_10yr,
        MAX(CASE WHEN series_key = 'V41552796' THEN value END)                   AS m2pp
    FROM raw.boc_observations
    GROUP BY 1
),
combined AS (
    SELECT
        s.period_date,
        to_char(s.period_date, 'YYYY-MM')                                        AS period_label,
        s.gdp, s.cpi, s.unemployment_rate, s.ippi, s.retail_trade,
        b.overnight_rate, b.cadusd, b.bond_10yr, b.m2pp,
        ROUND(
            (s.cpi
             / NULLIF(LAG(s.cpi, 12) OVER (ORDER BY s.period_date), 0) - 1
            ) * 100, 2
        )                                                                         AS cpi_yoy,
        ROUND(b.bond_10yr - b.overnight_rate, 4)                                  AS yield_spread,
        ROUND(
            s.unemployment_rate
            - LAG(s.unemployment_rate, 1) OVER (ORDER BY s.period_date), 2
        )                                                                         AS unemployment_delta
    FROM monthly_statcan s
    LEFT JOIN monthly_boc b ON s.period_date = b.period_date
)
SELECT
    period_date, period_label,
    gdp, cpi, unemployment_rate, ippi, retail_trade,
    overnight_rate, cadusd, bond_10yr, m2pp,
    cpi_yoy, yield_spread, unemployment_delta,
    now() AS updated_at
FROM combined
ON CONFLICT (period_date) DO UPDATE SET
    gdp                = EXCLUDED.gdp,
    cpi                = EXCLUDED.cpi,
    unemployment_rate  = EXCLUDED.unemployment_rate,
    ippi               = EXCLUDED.ippi,
    retail_trade       = EXCLUDED.retail_trade,
    overnight_rate     = EXCLUDED.overnight_rate,
    cadusd             = EXCLUDED.cadusd,
    bond_10yr          = EXCLUDED.bond_10yr,
    m2pp               = EXCLUDED.m2pp,
    cpi_yoy            = EXCLUDED.cpi_yoy,
    yield_spread       = EXCLUDED.yield_spread,
    unemployment_delta = EXCLUDED.unemployment_delta,
    updated_at         = EXCLUDED.updated_at;
