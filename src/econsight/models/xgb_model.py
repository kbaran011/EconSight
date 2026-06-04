from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import shap
from sklearn.metrics import mean_absolute_error, mean_squared_error
from xgboost import XGBRegressor

TARGETS: list[str] = ["cpi", "unemployment_rate", "overnight_rate"]
HORIZONS: list[int] = [1, 3]


@dataclass
class ModelMetrics:
    target: str
    horizon: int
    train_rmse: float
    test_rmse: float
    train_mae: float
    test_mae: float


class XGBForecastModel:
    def __init__(self, target: str, horizon: int) -> None:
        self.target = target
        self.horizon = horizon
        self._model: XGBRegressor | None = None

    def fit(self, X: pd.DataFrame, y: pd.Series) -> ModelMetrics:
        split = int(len(X) * 0.8)
        X_train, X_test = X.iloc[:split], X.iloc[split:]
        y_train, y_test = y.iloc[:split], y.iloc[split:]

        self._model = XGBRegressor(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            random_state=42,
            n_jobs=-1,
        )
        self._model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

        train_pred = self._model.predict(X_train)
        test_pred = self._model.predict(X_test)

        return ModelMetrics(
            target=self.target,
            horizon=self.horizon,
            train_rmse=float(np.sqrt(mean_squared_error(y_train, train_pred))),
            test_rmse=float(np.sqrt(mean_squared_error(y_test, test_pred))),
            train_mae=float(mean_absolute_error(y_train, train_pred)),
            test_mae=float(mean_absolute_error(y_test, test_pred)),
        )

    def predict(self, X: pd.DataFrame) -> float:
        if self._model is None:
            raise RuntimeError("Call fit() before predict()")
        return float(self._model.predict(X.iloc[[-1]])[0])

    def shap_values(self, X: pd.DataFrame) -> np.ndarray[Any, Any]:
        if self._model is None:
            raise RuntimeError("Call fit() before shap_values()")
        explainer = shap.TreeExplainer(self._model)
        return np.array(explainer.shap_values(X))

    def save(self, path: Path) -> None:
        joblib.dump(self._model, path)

    def load(self, path: Path) -> None:
        self._model = joblib.load(path)
