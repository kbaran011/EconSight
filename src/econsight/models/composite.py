from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

_RAW_COLS = [
    "gdp", "cpi", "unemployment_rate", "ippi", "retail_trade",
    "overnight_rate", "cadusd", "bond_10yr", "m2pp",
]
_FLIP_COLS = {"cpi", "unemployment_rate", "ippi", "yield_spread"}


class CompositeScorer:
    def __init__(self) -> None:
        self._scaler: StandardScaler | None = None
        self._pca: PCA | None = None
        self._weights: np.ndarray | None = None
        self._score_min: float | None = None
        self._score_max: float | None = None

    def _prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        data = df[_RAW_COLS].copy()
        data["yield_spread"] = data["bond_10yr"] - data["overnight_rate"]
        for col in _FLIP_COLS:
            data[col] = -data[col]
        return data

    def fit(self, df: pd.DataFrame) -> None:
        data = self._prepare(df)
        self._scaler = StandardScaler()
        scaled = self._scaler.fit_transform(data)
        self._pca = PCA(n_components=1, random_state=42)
        scores_raw = self._pca.fit_transform(scaled).ravel()
        self._weights = self._pca.components_[0]
        self._score_min = float(scores_raw.min())
        self._score_max = float(scores_raw.max())

    def score(self, df: pd.DataFrame) -> pd.DataFrame:
        if self._scaler is None or self._pca is None:
            raise RuntimeError("Call fit() before score()")
        data = self._prepare(df)
        scaled = self._scaler.transform(data)
        raw_scores = self._pca.transform(scaled).ravel()
        denom = (self._score_max - self._score_min) or 1.0  # type: ignore[operator]
        scores_100 = (raw_scores - self._score_min) / denom * 100.0
        scores_100 = np.clip(scores_100, 0.0, 100.0)

        col_names = list(data.columns)
        component_scores = [
            {
                col: float(scaled[i, j] * self._weights[j])  # type: ignore[index]
                for j, col in enumerate(col_names)
            }
            for i in range(len(df))
        ]
        return pd.DataFrame(
            {"score": scores_100, "component_scores": component_scores},
            index=df.index,
        )

    def save(self, path: Path) -> None:
        joblib.dump(
            {
                "scaler": self._scaler,
                "pca": self._pca,
                "weights": self._weights,
                "score_min": self._score_min,
                "score_max": self._score_max,
            },
            path,
        )

    def load(self, path: Path) -> None:
        data: dict[str, Any] = joblib.load(path)
        self._scaler = data["scaler"]
        self._pca = data["pca"]
        self._weights = data["weights"]
        self._score_min = data["score_min"]
        self._score_max = data["score_max"]
