import numpy as np
import pytest

from econsight.models.backtest_metrics import (
    diebold_mariano,
    mae,
    mase,
    rmse,
    skill_score,
)


def test_mae_rmse_basic():
    y = [1.0, 2.0, 3.0]
    p = [1.0, 2.0, 5.0]        # errors 0,0,2
    assert mae(y, p) == pytest.approx(2 / 3)
    assert rmse(y, p) == pytest.approx((4 / 3) ** 0.5)


def test_mase_scales_by_naive_mae():
    # scale series diffs are all 1.0 -> naive MAE = 1.0 -> MASE == MAE
    scale_series = [10.0, 11.0, 12.0, 13.0, 14.0]
    y = [20.0, 22.0]
    p = [20.0, 20.0]           # MAE = 1.0
    assert mase(y, p, scale_series) == pytest.approx(1.0)


def test_mase_below_one_means_beats_naive():
    scale_series = [0.0, 2.0, 4.0, 6.0]   # naive MAE = 2.0
    y = [10.0, 10.0]
    p = [10.5, 9.5]            # MAE = 0.5 -> MASE = 0.25
    assert mase(y, p, scale_series) == pytest.approx(0.25)


def test_mase_zero_scale_returns_nan():
    assert np.isnan(mase([1.0], [1.0], [5.0, 5.0, 5.0]))


def test_skill_score_sign():
    assert skill_score(rmse_model=0.5, rmse_baseline=1.0) == pytest.approx(0.5)
    assert skill_score(rmse_model=2.0, rmse_baseline=1.0) == pytest.approx(-1.0)
    assert np.isnan(skill_score(rmse_model=1.0, rmse_baseline=0.0))


def test_dm_detects_clear_superiority():
    rng = np.random.default_rng(0)
    n = 60
    base_err = rng.normal(0, 1.0, n)
    model_err = rng.normal(0, 0.3, n)      # clearly smaller errors
    stat, p = diebold_mariano(model_err, base_err, horizon=1)
    assert stat < 0          # negative => model loss < baseline loss
    assert p is not None and p < 0.05


def test_dm_no_difference_is_insignificant():
    rng = np.random.default_rng(1)
    e = rng.normal(0, 1.0, 60)
    stat, p = diebold_mariano(e.copy(), e.copy(), horizon=1)
    assert p is None or p > 0.05     # identical losses -> n/a or non-significant


def test_dm_small_sample_returns_none_pvalue():
    stat, p = diebold_mariano([0.1, 0.2, 0.3], [0.2, 0.3, 0.4], horizon=1)
    assert p is None


def test_dm_horizon_uses_autocovariance_terms():
    # Should run without error for h>1 and return a finite stat
    rng = np.random.default_rng(2)
    base_err = rng.normal(0, 1.0, 50)
    model_err = rng.normal(0, 0.5, 50)
    stat, p = diebold_mariano(model_err, base_err, horizon=3)
    assert np.isfinite(stat)
