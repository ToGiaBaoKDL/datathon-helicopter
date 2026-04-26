"""Simple baseline forecasters for benchmarking."""

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
