"""Metrics utilities for forecasting evaluation."""

from __future__ import annotations

import numpy as np


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    """Return MAE, RMSE, R² for true vs predicted arrays."""
    errors = y_pred - y_true
    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(errors**2)))
    denom = np.sum((y_true - np.mean(y_true)) ** 2)
    r2 = 0.0 if denom == 0 else float(1.0 - np.sum(errors**2) / denom)
    return {"mae": mae, "rmse": rmse, "r2": r2}


def fold_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    """Return MAE, RMSE, R² for a single CV fold (alias of compute_metrics)."""
    return compute_metrics(y_true, y_pred)
