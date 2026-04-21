from __future__ import annotations

import numpy as np
import pandas as pd

from datathon.modeling.baselines import compute_metrics, seasonal_naive


def test_seasonal_naive_repeats_tail_pattern() -> None:
    series = pd.Series([1, 2, 3, 4, 5, 6, 7])
    forecast = seasonal_naive(series, horizon=10, seasonal_period=3)
    assert forecast.tolist() == [5, 6, 7, 5, 6, 7, 5, 6, 7, 5]


def test_compute_metrics_basic_case() -> None:
    y_true = np.array([1.0, 2.0, 3.0])
    y_pred = np.array([1.0, 3.0, 2.0])
    metrics = compute_metrics(y_true, y_pred)

    assert metrics["mae"] >= 0
    assert metrics["rmse"] >= 0
    assert -1.0 <= metrics["r2"] <= 1.0
