# EconSight — Power BI Integration

## Opening the Report

1. Install [Power BI Desktop](https://powerbi.microsoft.com/desktop) (free)
2. Open `EconSight.pbix` (when available)
3. Click **Refresh** — the report pulls live data from the Railway API

No database credentials needed. The report connects to the public API endpoints.

## Data Sources

| Query | Endpoint | Content |
|---|---|---|
| Indicators | `/api/export/indicators.csv` | 13 macro indicators, 36 months |
| HealthScore | `/api/export/health-score.csv` | Composite health score history |
| Forecasts | `/api/export/forecasts.csv` | VAR/XGBoost forecasts with P10/P90 bands |

## Live Endpoints

Base URL: `https://econsight-production.up.railway.app`

- `GET /api/export/indicators.csv` — 36 months of 13 macro indicators (GDP, CPI, unemployment, etc.)
- `GET /api/export/health-score.csv` — composite health score history
- `GET /api/export/forecasts.csv` — VAR/XGBoost forecasts with P10/P90 scenario bands

## Connecting in Power BI Desktop

1. **Get Data** → **Web**
2. Paste the endpoint URL
3. Power BI detects CSV automatically → **Load**
4. Set `period_date` column type to **Date**
5. Set numeric columns to **Decimal Number**
6. Click **Refresh** on any schedule to get latest data

## Connecting in Other BI Tools

These endpoints work identically in:

| Tool | Connection method |
|---|---|
| **Excel** | Data → From Web → paste URL |
| **Tableau** | Web Data Connector → paste URL |
| **IBM Cognos Analytics** | Manage → Data server connections → REST → paste URL |
| **Google Looker Studio** | Custom connector → CSV URL |
