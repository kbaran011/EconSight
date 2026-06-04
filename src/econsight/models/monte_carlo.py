from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from econsight.models.xgb_model import HORIZONS, TARGETS, XGBForecastModel


@dataclass
class SimulationResult:
    # keyed by (target, horizon) tuple; each value has p10/p50/p90
    bands: dict[tuple[str, int], dict[str, float]]
    # keyed by "base"/"upside"/"downside"; derived from 3-month horizon
    scenarios: dict[str, dict[str, float]]


def simulate(
    models: dict[tuple[str, int], XGBForecastModel],
    X: pd.DataFrame,
    n_sims: int = 1000,
) -> SimulationResult:
    rng = np.random.default_rng(42)
    bands: dict[tuple[str, int], dict[str, float]] = {}

    for target in TARGETS:
        for h in HORIZONS:
            model = models[(target, h)]
            point = model.predict(X)
            # Compute in-sample predictions to derive residuals
            in_sample = np.array([
                float(model._model.predict(X.iloc[[i]])[0])  # type: ignore[union-attr]
                for i in range(len(X))
            ])
            residuals = in_sample - in_sample.mean()
            if len(residuals) == 0:
                residuals = np.array([0.0])
            sampled = rng.choice(residuals, size=n_sims, replace=True)
            paths = point + sampled
            bands[(target, h)] = {
                "p10": float(np.percentile(paths, 10)),
                "p50": float(np.percentile(paths, 50)),
                "p90": float(np.percentile(paths, 90)),
            }

    scenarios: dict[str, dict[str, float]] = {
        "base": {t: bands[(t, 3)]["p50"] for t in TARGETS},
        "upside": {
            "cpi":               bands[("cpi", 3)]["p10"],
            "unemployment_rate": bands[("unemployment_rate", 3)]["p10"],
            "overnight_rate":    bands[("overnight_rate", 3)]["p90"],
        },
        "downside": {
            "cpi":               bands[("cpi", 3)]["p90"],
            "unemployment_rate": bands[("unemployment_rate", 3)]["p90"],
            "overnight_rate":    bands[("overnight_rate", 3)]["p10"],
        },
    }

    return SimulationResult(bands=bands, scenarios=scenarios)
