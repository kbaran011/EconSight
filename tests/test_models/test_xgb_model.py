from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from econsight.models.features import build_feature_matrix
from econsight.models.xgb_model import (
    HORIZONS,
    TARGETS,
    ModelMetrics,
    XGBForecastModel,
)


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


def make_aligned_Xy(
    target: str = "cpi", horizon: int = 1, n: int = 30
) -> tuple[pd.DataFrame, pd.Series]:
    df = make_macro_df(n)
    X = build_feature_matrix(df)
    y = df[target].shift(-horizon).dropna()
    common_idx = X.index.intersection(y.index)
    return X.loc[common_idx], y.loc[common_idx]


def test_targets_and_horizons_constants() -> None:
    assert TARGETS == ["cpi", "unemployment_rate", "overnight_rate"]
    assert HORIZONS == [1, 3]


def test_fit_returns_model_metrics() -> None:
    X, y = make_aligned_Xy("cpi", 1)
    model = XGBForecastModel(target="cpi", horizon=1)
    metrics = model.fit(X, y)
    assert isinstance(metrics, ModelMetrics)
    assert metrics.target == "cpi"
    assert metrics.horizon == 1
    assert np.isfinite(metrics.train_rmse)
    assert np.isfinite(metrics.test_rmse)
    assert metrics.train_rmse >= 0
    assert metrics.test_rmse >= 0


def test_predict_returns_float() -> None:
    X, y = make_aligned_Xy("cpi", 1)
    model = XGBForecastModel(target="cpi", horizon=1)
    model.fit(X, y)
    result = model.predict(X)
    assert isinstance(result, float)
    assert np.isfinite(result)


def test_predict_uses_last_row() -> None:
    X, y = make_aligned_Xy("cpi", 1)
    model = XGBForecastModel(target="cpi", horizon=1)
    model.fit(X, y)
    result_full = model.predict(X)
    result_last = model.predict(X.iloc[[-1]])
    assert result_full == result_last


def test_shap_values_shape() -> None:
    X, y = make_aligned_Xy("cpi", 1)
    model = XGBForecastModel(target="cpi", horizon=1)
    model.fit(X, y)
    shap_vals = model.shap_values(X)
    assert shap_vals.shape == (len(X), X.shape[1])


def test_no_data_leakage_alignment() -> None:
    df = make_macro_df(30)
    X = build_feature_matrix(df)
    for h in [1, 3]:
        y = df["cpi"].shift(-h).dropna()
        common = X.index.intersection(y.index)
        # The intersection should be all X rows except the last h,
        # which have no aligned target (those would require future observations).
        assert len(common) == len(X) - h, f"Leakage for horizon {h}"


def test_save_load_roundtrip(tmp_path: Path) -> None:
    X, y = make_aligned_Xy("cpi", 1)
    model = XGBForecastModel(target="cpi", horizon=1)
    model.fit(X, y)
    path = tmp_path / "xgb_cpi_h1.pkl"
    model.save(path)
    loaded = XGBForecastModel(target="cpi", horizon=1)
    loaded.load(path)
    assert loaded.predict(X) == model.predict(X)


def test_raises_if_predict_before_fit() -> None:
    X, _ = make_aligned_Xy("cpi", 1)
    model = XGBForecastModel(target="cpi", horizon=1)
    with pytest.raises(RuntimeError, match="fit"):
        model.predict(X)
