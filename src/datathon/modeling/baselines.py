from __future__ import annotations

import numpy as np
import pandas as pd


def seasonal_naive(
    train_series: pd.Series,
    horizon: int,
    seasonal_period: int = 7,
) -> np.ndarray:
    if len(train_series) < seasonal_period:
        last_value = float(train_series.iloc[-1])
        return np.repeat(last_value, horizon)

    tail = train_series.iloc[-seasonal_period:].to_numpy()
    repeats = int(np.ceil(horizon / seasonal_period))
    forecast = np.tile(tail, repeats)[:horizon]
    return forecast


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    errors = y_pred - y_true
    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(errors**2)))

    denominator = np.sum((y_true - np.mean(y_true)) ** 2)
    r2 = 0.0 if denominator == 0 else float(1.0 - (np.sum(errors**2) / denominator))

    return {"mae": mae, "rmse": rmse, "r2": r2}
