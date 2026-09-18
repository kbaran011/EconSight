from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from scipy import stats


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


def diebold_mariano(
    model_errors: Sequence[float],
    baseline_errors: Sequence[float],
    horizon: int = 1,
    power: int = 2,
) -> tuple[float, float | None]:
    """Diebold–Mariano test with Harvey–Leybourne–Newbold small-sample correction.

    Loss differential d = |model_err|^power - |baseline_err|^power.
    Negative mean(d) => the model has lower loss (is better). For horizon > 1 the
    forecasts overlap, so the long-run variance of the mean includes autocovariances
    up to lag ``horizon - 1``. Returns (dm_statistic, p_value); p_value is None when
    the sample is too small or the variance is degenerate.
    """
    e1 = np.asarray(model_errors, dtype=float)
    e2 = np.asarray(baseline_errors, dtype=float)
    d = np.abs(e1) ** power - np.abs(e2) ** power
    n = d.size
    if n < 8:
        return (float("nan"), None)
    d_bar = float(np.mean(d))
    dev = d - d_bar
    gamma0 = float(np.mean(dev**2))
    acov = 0.0
    for k in range(1, horizon):
        if k < n:
            acov += float(np.mean(dev[k:] * dev[:-k]))
    var_dbar = (gamma0 + 2.0 * acov) / n
    if not np.isfinite(var_dbar) or var_dbar <= 0.0:
        return (float("nan"), None)
    dm = d_bar / np.sqrt(var_dbar)
    # HLN correction factor
    factor = (n + 1 - 2 * horizon + horizon * (horizon - 1) / n) / n
    if factor <= 0:
        return (float(dm), None)
    dm_hln = float(dm * np.sqrt(factor))
    p_value = float(2.0 * stats.t.cdf(-abs(dm_hln), df=n - 1))
    return (dm_hln, p_value)
