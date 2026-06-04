from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
import psycopg

_RAW_COLS = [
    "gdp", "cpi", "unemployment_rate", "ippi", "retail_trade",
    "overnight_rate", "cadusd", "bond_10yr", "m2pp",
]

_SQL = """
    SELECT period_date, gdp, cpi, unemployment_rate, ippi, retail_trade,
           overnight_rate, cadusd, bond_10yr, m2pp
    FROM marts.mart_monthly_macro_indicators
    WHERE data_complete = TRUE
    ORDER BY period_date ASC
"""


async def load_mart(conn: psycopg.AsyncConnection[Any]) -> pd.DataFrame:
    async with conn.cursor() as cur:
        await cur.execute(_SQL)
        rows = await cur.fetchall()
        cols = [d[0] for d in cur.description]  # type: ignore[union-attr]
    df = pd.DataFrame(rows, columns=cols)
    df["period_date"] = df["period_date"].apply(
        lambda v: v if isinstance(v, date) else v.date()
    )
    df = df.set_index("period_date").sort_index()
    df = df[_RAW_COLS].apply(pd.to_numeric, errors="coerce")
    return df


def build_feature_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Build ~90-column feature matrix from 9-column raw indicator DataFrame."""
    frames: list[pd.DataFrame] = [df.copy()]

    for col in _RAW_COLS:
        s = df[col]
        # Lags
        for lag in [1, 2, 3, 6, 12]:
            frames.append(s.shift(lag).rename(f"{col}_lag{lag}").to_frame())
        # Rolling means (shift(1) avoids look-ahead)
        for window in [3, 6]:
            frames.append(
                s.shift(1).rolling(window).mean().rename(f"{col}_roll{window}").to_frame()
            )
        # First difference
        frames.append(s.diff().rename(f"{col}_diff").to_frame())
        # YoY change
        frames.append(
            ((s - s.shift(12)) / s.shift(12).abs() * 100).rename(f"{col}_yoy").to_frame()
        )

    X = pd.concat(frames, axis=1)
    X = X.dropna()
    return X
