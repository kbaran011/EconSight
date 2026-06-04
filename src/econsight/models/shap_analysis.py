from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from econsight.models.xgb_model import XGBForecastModel


@dataclass
class SHAPSummary:
    values: np.ndarray  # shape: (n_samples, n_features)
    mean_abs: dict[str, float]  # feature → mean |SHAP value|
    top_features: list[str]  # top-10 features by mean |SHAP value|


def compute_shap_summary(model: XGBForecastModel, X: pd.DataFrame) -> SHAPSummary:
    raw = model.shap_values(X)
    mean_abs = {
        col: float(np.abs(raw[:, i]).mean())
        for i, col in enumerate(X.columns)
    }
    top_features = sorted(mean_abs, key=lambda k: mean_abs[k], reverse=True)[:10]
    return SHAPSummary(values=raw, mean_abs=mean_abs, top_features=top_features)
