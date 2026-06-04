from datetime import date
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pandas as pd

from econsight.models.features import build_feature_matrix, load_mart


def make_macro_df(n: int = 30) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    dates = [date(2015 + i // 12, i % 12 + 1, 1) for i in range(n)]
    return pd.DataFrame(
        {
            "gdp":               rng.uniform(2_000_000, 2_600_000, n),
            "cpi":               rng.uniform(120.0, 170.0, n),
            "unemployment_rate": rng.uniform(5.0, 10.0, n),
            "ippi":              rng.uniform(90.0, 130.0, n),
            "retail_trade":      rng.uniform(50_000, 70_000, n),
            "overnight_rate":    rng.uniform(0.25, 5.0, n),
            "cadusd":            rng.uniform(0.70, 0.85, n),
            "bond_10yr":         rng.uniform(0.5, 4.0, n),
            "m2pp":              rng.uniform(1_800_000, 2_500_000, n),
        },
        index=dates,
    )


def test_lag_columns_exist() -> None:
    X = build_feature_matrix(make_macro_df(30))
    for col in ["cpi", "overnight_rate"]:
        for lag in [1, 2, 3, 6, 12]:
            assert f"{col}_lag{lag}" in X.columns


def test_rolling_columns_exist() -> None:
    X = build_feature_matrix(make_macro_df(30))
    for col in ["cpi", "gdp"]:
        assert f"{col}_roll3" in X.columns
        assert f"{col}_roll6" in X.columns


def test_diff_and_yoy_columns_exist() -> None:
    X = build_feature_matrix(make_macro_df(30))
    assert "cpi_diff" in X.columns
    assert "cpi_yoy" in X.columns


def test_no_nan_in_output() -> None:
    X = build_feature_matrix(make_macro_df(30))
    assert not X.isnull().any().any(), "Feature matrix must not contain NaN"


def test_rows_dropped_for_lag_window() -> None:
    df = make_macro_df(30)
    X = build_feature_matrix(df)
    assert len(X) <= len(df) - 12


def test_lag1_value_correct() -> None:
    df = make_macro_df(20)
    X = build_feature_matrix(df)
    first_kept = X.index[0]
    pos_in_df = list(df.index).index(first_kept)
    expected = float(df["cpi"].iloc[pos_in_df - 1])
    assert abs(float(X.loc[first_kept, "cpi_lag1"]) - expected) < 1e-9


def test_diff_value_correct() -> None:
    df = make_macro_df(20)
    X = build_feature_matrix(df)
    first_kept = X.index[0]
    pos = list(df.index).index(first_kept)
    expected = float(df["cpi"].iloc[pos]) - float(df["cpi"].iloc[pos - 1])
    assert abs(float(X.loc[first_kept, "cpi_diff"]) - expected) < 1e-9


async def test_load_mart_returns_correct_columns() -> None:
    mock_conn = MagicMock()
    mock_cur = AsyncMock()
    mock_cur.description = [
        (col,) for col in [
            "period_date", "gdp", "cpi", "unemployment_rate", "ippi",
            "retail_trade", "overnight_rate", "cadusd", "bond_10yr", "m2pp",
        ]
    ]
    mock_cur.fetchall = AsyncMock(return_value=[
        (date(2020, 1, 1), 2_100_000.0, 136.0, 5.8, 110.0, 57_000.0, 1.75, 0.74, 1.44, 1_950_000.0),
        (date(2020, 2, 1), 2_110_000.0, 136.5, 5.7, 111.0, 58_000.0, 1.75, 0.75, 1.46, 1_960_000.0),
    ])
    mock_conn.cursor.return_value.__aenter__ = AsyncMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__aexit__ = AsyncMock(return_value=None)

    df = await load_mart(mock_conn)

    expected_cols = {"gdp", "cpi", "unemployment_rate", "ippi", "retail_trade",
                     "overnight_rate", "cadusd", "bond_10yr", "m2pp"}
    assert set(df.columns) == expected_cols
    assert len(df) == 2
    assert isinstance(df.index[0], date)
