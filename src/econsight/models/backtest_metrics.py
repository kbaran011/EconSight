from __future__ import annotations

from collections.abc import Sequence

import numpy as np


def _arr(x: Sequence[float]) -> np.ndarray:
    return np.asarray(x, dtype=float)


def mae(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    return float(np.mean(np.abs(_arr(y_true) - _arr(y_pred))))


def rmse(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    return float(np.sqrt(np.mean((_arr(y_true) - _arr(y_pred)) ** 2)))


def mase(
    y_true: Sequence[float], y_pred: Sequence[float], scale_series: Sequence[float]
) -> float:
    """Mean Absolute Scaled Error (Hyndman & Koehler).

    Scale = MAE of the one-step naive forecast on ``scale_series`` (the target's
    in-sample level history). MASE < 1 means the model beats the naive benchmark.
    """
    scale = float(np.mean(np.abs(np.diff(_arr(scale_series)))))
    if not np.isfinite(scale) or scale == 0.0:
        return float("nan")
    return mae(y_true, y_pred) / scale


def skill_score(rmse_model: float, rmse_baseline: float) -> float:
    """1 - RMSE_model / RMSE_baseline. Positive => better than baseline."""
    if not np.isfinite(rmse_baseline) or rmse_baseline == 0.0:
        return float("nan")
    return 1.0 - rmse_model / rmse_baseline
