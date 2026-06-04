from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from econsight.models.var_model import VARModel

_TARGET_COLS = ["cpi", "unemployment_rate", "overnight_rate"]


def make_target_df(n: int = 60) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    dates = [date(2015 + i // 12, i % 12 + 1, 1) for i in range(n)]
    return pd.DataFrame(
        {
            "cpi":               rng.uniform(120.0, 170.0, n),
            "unemployment_rate": rng.uniform(5.0, 10.0, n),
            "overnight_rate":    rng.uniform(0.25, 5.0, n),
        },
        index=dates,
    )


def _make_patches(mock_forecast: np.ndarray):
    johansen_patch = patch("econsight.models.var_model.coint_johansen")
    var_patch = patch("econsight.models.var_model.VAR")

    mock_johansen_result = MagicMock()
    mock_johansen_result.lr1 = np.array([1.0, 0.5, 0.2])
    mock_johansen_result.cvt = np.array([[10.0] * 3] * 3)

    mock_fit_result = MagicMock()
    mock_fit_result.k_ar = 2
    mock_fit_result.endog = np.zeros((60, 3))
    mock_fit_result.forecast.return_value = mock_forecast

    mock_var_instance = MagicMock()
    mock_var_instance.fit.return_value = mock_fit_result
    mock_var_instance.select_order.return_value.aic = 2

    return johansen_patch, var_patch, mock_johansen_result, mock_var_instance


def test_predict_returns_correct_structure() -> None:
    df = make_target_df()
    mock_forecast = np.array([[130.0, 6.5, 2.0], [131.0, 6.6, 2.1], [132.0, 6.7, 2.2]])

    johansen_p, var_p, mock_j, mock_v = _make_patches(mock_forecast)
    with johansen_p as mj, var_p as mv:
        mj.return_value = mock_j
        mv.return_value = mock_v
        model = VARModel()
        model.fit(df)
        result = model.predict(horizons=[1, 3])

    assert set(result.keys()) == {1, 3}
    for h in [1, 3]:
        assert set(result[h].keys()) == set(_TARGET_COLS)
        for v in result[h].values():
            assert isinstance(v, float)


def test_predict_values_match_forecast_array() -> None:
    df = make_target_df()
    mock_forecast = np.array([[130.0, 6.5, 2.0], [131.0, 6.6, 2.1], [132.0, 6.7, 2.2]])

    johansen_p, var_p, mock_j, mock_v = _make_patches(mock_forecast)
    with johansen_p as mj, var_p as mv:
        mj.return_value = mock_j
        mv.return_value = mock_v
        model = VARModel()
        model.fit(df)
        result = model.predict(horizons=[1, 3])

    assert result[1]["cpi"] == pytest.approx(130.0)
    assert result[1]["unemployment_rate"] == pytest.approx(6.5)
    assert result[3]["cpi"] == pytest.approx(132.0)


def test_raises_if_predict_before_fit() -> None:
    model = VARModel()
    with pytest.raises(RuntimeError, match="fit"):
        model.predict(horizons=[1])


def test_save_load_roundtrip(tmp_path: Path) -> None:
    df = make_target_df()
    mock_forecast = np.array([[130.0, 6.5, 2.0], [131.0, 6.6, 2.1], [132.0, 6.7, 2.2]])

    johansen_p, var_p, mock_j, mock_v = _make_patches(mock_forecast)
    path = tmp_path / "var_model.pkl"

    saved_payload: dict = {}

    def fake_dump(obj: dict, p: Path) -> None:
        saved_payload.update(obj)

    def fake_load(p: Path) -> dict:
        return saved_payload

    with (
        johansen_p as mj,
        var_p as mv,
        patch("econsight.models.var_model.joblib.dump", side_effect=fake_dump),
        patch("econsight.models.var_model.joblib.load", side_effect=fake_load),
    ):
        mj.return_value = mock_j
        mv.return_value = mock_v
        model = VARModel()
        model.fit(df)
        model.save(path)

        loaded = VARModel()
        loaded.load(path)

    assert loaded._fitted_model is not None
