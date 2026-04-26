from __future__ import annotations

import numpy as np
import pandas as pd

from datathon.modeling.baselines import seasonal_naive
from datathon.modeling.metrics import compute_metrics


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


def test_seasonal_naive_short_series() -> None:
    """When series is shorter than seasonal_period, repeat last value."""
    series = pd.Series([1, 2])
    forecast = seasonal_naive(series, horizon=5, seasonal_period=7)
    assert forecast.tolist() == [2.0, 2.0, 2.0, 2.0, 2.0]


def test_compute_metrics_perfect_prediction() -> None:
    y_true = np.array([1.0, 2.0, 3.0])
    metrics = compute_metrics(y_true, y_true)
    assert metrics["mae"] == 0.0
    assert metrics["rmse"] == 0.0
    assert metrics["r2"] == 1.0


def test_compute_metrics_constant_y_true_r2_zero() -> None:
    """R2 is defined as 0 when y_true has zero variance."""
    y_true = np.array([5.0, 5.0, 5.0])
    y_pred = np.array([4.0, 5.0, 6.0])
    metrics = compute_metrics(y_true, y_pred)
    assert metrics["r2"] == 0.0
