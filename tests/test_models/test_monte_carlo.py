from datetime import date

import numpy as np
import pandas as pd
import pytest

from econsight.models.features import build_feature_matrix
from econsight.models.monte_carlo import SimulationResult, simulate
from econsight.models.xgb_model import HORIZONS, TARGETS, XGBForecastModel


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


@pytest.fixture(scope="module")
def fitted_models() -> dict:
    df = make_macro_df(30)
    X = build_feature_matrix(df)
    models = {}
    for target in TARGETS:
        for h in HORIZONS:
            y = df[target].shift(-h).dropna()
            common = X.index.intersection(y.index)
            model = XGBForecastModel(target=target, horizon=h)
            model.fit(X.loc[common], y.loc[common])
            models[(target, h)] = model
    return {"X": X, "models": models}


def test_simulation_result_has_correct_band_keys(fitted_models: dict) -> None:
    sim = simulate(fitted_models["models"], fitted_models["X"], n_sims=50)
    expected_keys = {(t, h) for t in TARGETS for h in HORIZONS}
    assert set(sim.bands.keys()) == expected_keys


def test_percentile_ordering(fitted_models: dict) -> None:
    sim = simulate(fitted_models["models"], fitted_models["X"], n_sims=50)
    for key, band in sim.bands.items():
        assert band["p10"] <= band["p50"] <= band["p90"], (
            f"Percentile ordering violated for {key}"
        )


def test_scenario_keys_present(fitted_models: dict) -> None:
    sim = simulate(fitted_models["models"], fitted_models["X"], n_sims=50)
    assert set(sim.scenarios.keys()) == {"base", "upside", "downside"}


def test_scenario_targets_present(fitted_models: dict) -> None:
    sim = simulate(fitted_models["models"], fitted_models["X"], n_sims=50)
    for scenario in sim.scenarios.values():
        assert set(scenario.keys()) == set(TARGETS)


def test_simulation_result_is_dataclass() -> None:
    from dataclasses import fields
    field_names = {f.name for f in fields(SimulationResult)}
    assert "bands" in field_names
    assert "scenarios" in field_names
