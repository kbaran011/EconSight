from __future__ import annotations

import re

from groq import AsyncGroq

from econsight.api.schemas import RAGResponse
from econsight.config import get_logger, settings
from econsight.db.connection import db_connection_readonly
from econsight.rag.retriever import retrieve

logger = get_logger(__name__)

_client = AsyncGroq(api_key=settings.groq_api_key)
_MODEL = "llama-3.3-70b-versatile"

_SCHEMA_CONTEXT = """
Available tables (SELECT only, marts schema):
- marts.mart_monthly_macro_indicators: period_date, gdp, cpi, unemployment_rate, ippi,
  retail_trade, overnight_rate, cadusd, bond_10yr, m2pp, cpi_yoy, yield_spread,
  unemployment_delta, data_complete
- marts.model_forecasts: period_date, target, horizon_months, model_type, point_forecast,
  p10, p50, p90, scenario_base, scenario_upside, scenario_downside, created_at
- marts.economic_health_score: period_date, score, component_scores, updated_at
"""

_DANGEROUS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE)\b|;",
    re.IGNORECASE,
)


def _is_safe_sql(query: str) -> bool:
    return not bool(_DANGEROUS.search(query))


def _text(response: object) -> str:
    return response.choices[0].message.content or ""  # type: ignore[attr-defined]


async def _classify(question: str) -> str:
    response = await _client.chat.completions.create(
        model=_MODEL,
        max_tokens=10,
        messages=[
            {
                "role": "system",
                "content": (
                    "Classify the question as 'sql' if it asks for specific data values, dates, "
                    "or statistics that need a database query, or 'narrative' if it asks for "
                    "analysis, explanation, or insight. "
                    "Reply with only the word 'sql' or 'narrative'."
                ),
            },
            {"role": "user", "content": question},
        ],
    )
    return _text(response).strip().lower()


async def _sql_answer(question: str) -> RAGResponse:
    response = await _client.chat.completions.create(
        model=_MODEL,
        max_tokens=256,
        messages=[
            {
                "role": "system",
                "content": (
                    "Generate a single read-only PostgreSQL SELECT query to answer the question. "
                    f"Use only these tables:\n{_SCHEMA_CONTEXT}\n"
                    "Reply with only the SQL query, no explanation, no markdown."
                ),
            },
            {"role": "user", "content": question},
        ],
    )
    sql = _text(response).strip().removeprefix("```sql").removesuffix("```").strip()

    if not _is_safe_sql(sql):
        return RAGResponse(
            answer="I can only run read-only SELECT queries on the marts tables.",
            sources=["database"],
            query_type="sql",
        )

    try:
        async with db_connection_readonly() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql)
                rows = await cur.fetchmany(20)
                cols = [d[0] for d in (cur.description or [])]

        if not rows:
            answer = "No data found for that query."
        else:
            header = " | ".join(cols)
            body = "\n".join(" | ".join(str(v) for v in row) for row in rows)
            answer = f"{header}\n{'---' * len(cols)}\n{body}"
    except Exception as exc:
        answer = f"Query failed: {exc}"

    return RAGResponse(answer=answer, sources=["database"], query_type="sql")


async def _narrative_answer(question: str) -> RAGResponse:
    chunks = await retrieve(question, top_k=5)
    if not chunks:
        return RAGResponse(
            answer=(
                "The analysis report has not been indexed yet. "
                "Please run the Phase 2 notebook first."
            ),
            sources=[],
            query_type="narrative",
        )
    context = "\n\n".join(f"[{c['title']}]\n{c['text']}" for c in chunks)
    response = await _client.chat.completions.create(
        model=_MODEL,
        max_tokens=512,
        messages=[
            {
                "role": "system",
                "content": (
                    "Answer the question using only the provided context."
                    " Be concise and factual."
                ),
            },
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
        ],
    )
    sources = list({c["title"] for c in chunks if c["title"]})
    return RAGResponse(
        answer=_text(response),
        sources=sources,
        query_type="narrative",
    )


async def answer(question: str) -> RAGResponse:
    query_type = await _classify(question)
    logger.info("rag.query", question=question[:80], type=query_type)
    if query_type == "sql":
        return await _sql_answer(question)
    return await _narrative_answer(question)
