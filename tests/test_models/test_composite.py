from datetime import date

import numpy as np
import pandas as pd
import pytest

from econsight.models.composite import CompositeScorer

_EXPECTED_COMPONENT_KEYS = {
    "gdp", "cpi", "unemployment_rate", "ippi", "retail_trade",
    "overnight_rate", "cadusd", "bond_10yr", "m2pp", "yield_spread",
}


def make_macro_df(n: int = 20) -> pd.DataFrame:
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


def test_score_in_range() -> None:
    df = make_macro_df(20)
    scorer = CompositeScorer()
    scorer.fit(df)
    result = scorer.score(df)
    assert (result["score"] >= 0).all()
    assert (result["score"] <= 100).all()


def test_score_output_has_correct_columns() -> None:
    df = make_macro_df(20)
    scorer = CompositeScorer()
    scorer.fit(df)
    result = scorer.score(df)
    assert "score" in result.columns
    assert "component_scores" in result.columns


def test_component_scores_has_10_keys() -> None:
    df = make_macro_df(20)
    scorer = CompositeScorer()
    scorer.fit(df)
    result = scorer.score(df)
    for cs in result["component_scores"]:
        assert set(cs.keys()) == _EXPECTED_COMPONENT_KEYS


def test_score_output_length_matches_input() -> None:
    df = make_macro_df(20)
    scorer = CompositeScorer()
    scorer.fit(df)
    result = scorer.score(df)
    assert len(result) == len(df)


def test_raises_if_score_before_fit() -> None:
    scorer = CompositeScorer()
    with pytest.raises(RuntimeError, match="fit"):
        scorer.score(make_macro_df(10))


def test_save_load_roundtrip(tmp_path) -> None:
    from pathlib import Path
    df = make_macro_df(20)
    scorer = CompositeScorer()
    scorer.fit(df)
    path = Path(str(tmp_path)) / "scorer.pkl"
    scorer.save(path)
    loaded = CompositeScorer()
    loaded.load(path)
    original = scorer.score(df)["score"].values
    restored = loaded.score(df)["score"].values
    np.testing.assert_allclose(original, restored)
