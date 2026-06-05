from __future__ import annotations

import asyncio
import string

import psycopg

from econsight.config import get_logger

logger = get_logger(__name__)

_BRIEF_CSS_TMPL = string.Template("""
body { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; margin: 40px; color: #1a1a2e; }
h1 { font-size: 28px; color: #16213e; border-bottom: 3px solid #0f3460; padding-bottom: 10px; }
h2 { font-size: 18px; color: #0f3460; margin-top: 28px; }
.score { font-size: 72px; font-weight: bold; color: $score_color; }
.delta { font-size: 18px; color: #555; }
table { border-collapse: collapse; width: 100%; margin-top: 10px; }
th { background: #0f3460; color: white; padding: 8px 12px; text-align: left; }
td { padding: 7px 12px; border-bottom: 1px solid #ddd; }
tr:nth-child(even) { background: #f8f9fa; }
.outlook { background: #eef2ff; border-left: 4px solid #0f3460; padding: 14px; margin-top: 14px; }
""")


def _score_color(score: float) -> str:
    if score >= 60:
        return "#16a34a"
    if score >= 40:
        return "#d97706"
    return "#dc2626"


def _render_brief_html(
    month_label: str,
    latest_score: float,
    score_delta: float,
    risk_indicators: list[tuple[str, float, str]],
    forecasts: list[tuple[str, float, float, float, float]],
    outlook_paragraph: str,
) -> str:
    delta_sign = "+" if score_delta >= 0 else ""
    risk_rows = "".join(
        f"<tr><td>{name.replace('_', ' ').title()}</td>"
        f"<td>{value:.2f}</td><td>{trend}</td></tr>"
        for name, value, trend in risk_indicators
    )
    forecast_rows = "".join(
        f"<tr><td>{name}</td><td>{v1:.3f}</td><td>{v3:.3f}</td>"
        f"<td>{x1:.3f}</td><td>{x3:.3f}</td></tr>"
        for name, v1, v3, x1, x3 in forecasts
    )
    css = _BRIEF_CSS_TMPL.substitute(score_color=_score_color(latest_score))
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><style>{css}</style></head>
<body>
<h1>EconSight — Canadian Economic Outlook</h1>
<p style="color:#666;font-size:14px;margin-top:-8px">{month_label}</p>

<h2>Economic Health Score</h2>
<div class="score">{latest_score:.1f}<span style="font-size:24px">/100</span></div>
<div class="delta">{delta_sign}{score_delta:.1f} from prior month</div>

<h2>Key Risk Indicators</h2>
<table>
<tr><th>Indicator</th><th>Latest Value</th><th>Trend</th></tr>
{risk_rows}
</table>

<h2>Forecast Summary</h2>
<table>
<tr><th>Target</th><th>VAR 1M</th><th>VAR 3M</th><th>XGB 1M</th><th>XGB 3M</th></tr>
{forecast_rows}
</table>

<h2>Economic Outlook</h2>
<div class="outlook">{outlook_paragraph}</div>
</body>
</html>"""


async def _build_outlook(
    score: float, forecasts: list[tuple[str, float, float, float, float]]
) -> str:
    try:
        from anthropic import AsyncAnthropic
        client = AsyncAnthropic()
        fc_text = "; ".join(
            f"{name}: {x1:.2f} (1M), {x3:.2f} (3M)"
            for name, _, _, x1, x3 in forecasts
        )
        prompt = (
            f"Write a 2-sentence plain-language economic outlook for Canadian SMEs. "
            f"Health score: {score:.1f}/100. Forecasts: {fc_text}."
        )
        r = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}],
        )
        block = r.content[0]
        from anthropic.types import TextBlock
        return block.text if isinstance(block, TextBlock) else str(block)
    except Exception:
        return (
            "The economic outlook remains mixed, with moderate inflationary pressure "
            "and stable labour market conditions."
        )


async def generate_brief(conn: psycopg.AsyncConnection) -> bytes:
    async with conn.cursor() as cur:
        await cur.execute(
            "SELECT period_date, score FROM marts.economic_health_score "
            "ORDER BY period_date DESC LIMIT 2"
        )
        score_rows = await cur.fetchall()
        await cur.execute(
            "SELECT target, horizon_months, model_type, point_forecast "
            "FROM marts.model_forecasts ORDER BY target, horizon_months, model_type"
        )
        forecast_rows = await cur.fetchall()
        await cur.execute(
            "SELECT component_scores FROM marts.economic_health_score "
            "ORDER BY period_date DESC LIMIT 1"
        )
        comp_row = await cur.fetchone()

    latest_score = float(score_rows[0][1]) if score_rows else 50.0
    prev_score = float(score_rows[1][1]) if len(score_rows) > 1 else latest_score
    delta = latest_score - prev_score
    month_label = str(score_rows[0][0]) if score_rows else "N/A"

    comp_scores: dict[str, float] = {}
    if comp_row and comp_row[0]:
        comp_scores = {k: float(v) for k, v in comp_row[0].items()}

    risk_indicators = sorted(comp_scores.items(), key=lambda x: x[1])[:3]
    risk_list = [(k, abs(v), "↓" if v < 0 else "↑") for k, v in risk_indicators]

    # SQL column order: target(0), horizon_months(1), model_type(2), point_forecast(3)
    var_1m: dict[str, float] = {}
    var_3m: dict[str, float] = {}
    xgb_1m: dict[str, float] = {}
    xgb_3m: dict[str, float] = {}
    for row in forecast_rows:
        target, horizon, model, pf = str(row[0]), int(row[1]), str(row[2]), float(row[3])
        if model == "var" and horizon == 1:
            var_1m[target] = pf
        elif model == "var" and horizon == 3:
            var_3m[target] = pf
        elif model == "xgboost" and horizon == 1:
            xgb_1m[target] = pf
        elif model == "xgboost" and horizon == 3:
            xgb_3m[target] = pf

    fc_table = [
        (
            t.replace("_", " ").title(),
            var_1m.get(t, 0.0), var_3m.get(t, 0.0),
            xgb_1m.get(t, 0.0), xgb_3m.get(t, 0.0),
        )
        for t in ["cpi", "unemployment_rate", "overnight_rate"]
    ]

    outlook = await _build_outlook(latest_score, fc_table)
    html = _render_brief_html(month_label, latest_score, delta, risk_list, fc_table, outlook)

    def _render_pdf() -> bytes:
        from weasyprint import HTML  # lazy import — requires GTK at runtime only
        return bytes(HTML(string=html).write_pdf())

    return await asyncio.to_thread(_render_pdf)
