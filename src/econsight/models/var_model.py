from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from statsmodels.tsa.vector_ar.var_model import VAR
from statsmodels.tsa.vector_ar.vecm import VECM, coint_johansen

_TARGET_COLS = ["cpi", "unemployment_rate", "overnight_rate"]
_MAX_LAG = 6


class VARModel:
    def __init__(self) -> None:
        self._fitted_model: Any = None
        self._model_type: str | None = None

    def fit(self, df: pd.DataFrame) -> None:
        data = df[_TARGET_COLS].dropna()
        johansen = coint_johansen(data.values, det_order=0, k_ar_diff=1)
        n_coint = int(np.sum(johansen.lr1 > johansen.cvt[:, 1]))
        if n_coint > 0:
            self._model_type = "vecm"
            model = VECM(data, k_ar_diff=1, coint_rank=n_coint, deterministic="ci")
            self._fitted_model = model.fit()
        else:
            self._model_type = "var"
            var_model = VAR(data.diff().dropna())
            lag_order = var_model.select_order(maxlags=_MAX_LAG).aic
            lag_order = min(max(int(lag_order), 1), _MAX_LAG)
            self._fitted_model = var_model.fit(lag_order)

    def predict(self, horizons: list[int]) -> dict[int, dict[str, float]]:
        if self._fitted_model is None:
            raise RuntimeError("Call fit() before predict()")
        max_h = max(horizons)
        if self._model_type == "var":
            k_ar = self._fitted_model.k_ar
            last_obs = self._fitted_model.endog[-k_ar:]
            raw = self._fitted_model.forecast(last_obs, steps=max_h)
        else:
            raw = self._fitted_model.predict(steps=max_h)

        result: dict[int, dict[str, float]] = {}
        for h in horizons:
            row = raw[h - 1]
            result[h] = {col: float(row[i]) for i, col in enumerate(_TARGET_COLS)}
        return result

    def save(self, path: Path) -> None:
        joblib.dump({"model": self._fitted_model, "type": self._model_type}, path)

    def load(self, path: Path) -> None:
        data: dict[str, Any] = joblib.load(path)
        self._fitted_model = data["model"]
        self._model_type = data["type"]
