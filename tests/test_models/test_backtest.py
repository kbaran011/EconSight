import numpy as np
import pandas as pd
import pytest

from econsight.models.backtest import build_pairs, walk_forward, NaiveRW, SeasonalNaive


def _levels(n=40):
    idx = pd.date_range("2015-01-01", periods=n, freq="MS").date
    # simple trending series per target
    data = {
        "cpi": np.linspace(100, 140, n),
        "unemployment_rate": np.linspace(7, 5, n),
        "overnight_rate": np.linspace(0.5, 4.5, n),
    }
    return pd.DataFrame(data, index=pd.Index(idx, name="period_date"))


def test_build_pairs_target_date_is_h_ahead():
    lv = _levels(12)
    X = pd.DataFrame({"f": range(len(lv))}, index=lv.index)
    pairs = build_pairs(lv, X, "cpi", horizon=3)
    # first origin's target date is 3 rows ahead; last h rows have no target
    assert pairs.iloc[0]["target_date"] == lv.index[3]
    assert len(pairs) == len(lv) - 3


def test_walk_forward_no_lookahead_invariant():
    """Every training pair used at an origin must have target_date <= origin."""
    lv = _levels(40)
    X = pd.DataFrame({"f": np.arange(len(lv), dtype=float)}, index=lv.index)
    horizon = 3
    seen = walk_forward(lv, X, "cpi", horizon, models=[NaiveRW()], min_train=12)
    # walk_forward exposes the audited training window via the recorded folds;
    # assert the naive RW prediction equals the level at the origin (y_t)
    for fold in seen["naive_rw"]:
        origin_level = lv.loc[fold.origin_date, "cpi"]
        assert fold.y_pred == pytest.approx(origin_level)


def test_walk_forward_records_training_audit():
    lv = _levels(30)
    X = pd.DataFrame({"f": np.arange(len(lv), dtype=float)}, index=lv.index)
    horizon = 1
    folds = walk_forward(lv, X, "cpi", horizon, models=[NaiveRW()], min_train=10)["naive_rw"]
    for f in folds:
        # audit: max training target_date must not exceed the origin
        assert f.max_train_target_date <= f.origin_date


def test_seasonal_naive_uses_value_12_months_before_target():
    lv = _levels(30)
    X = pd.DataFrame({"f": np.arange(len(lv), dtype=float)}, index=lv.index)
    folds = walk_forward(lv, X, "cpi", 1, models=[SeasonalNaive()], min_train=14)["seasonal_naive"]
    f = folds[0]
    # target_date - 12 months value
    tpos = list(lv.index).index(f.target_date)
    assert f.y_pred == pytest.approx(lv["cpi"].iloc[tpos - 12])
