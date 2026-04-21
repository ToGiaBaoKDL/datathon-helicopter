"""Recursive multi-step forecasting helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd

from datathon.modeling.forecasters.base import BaseForecaster

# Calendar features are always computable from the date.
CALENDAR_FEATURES = [
    "year",
    "month",
    "quarter",
    "day_of_week",
    "is_weekend",
    "day_of_month",
    "days_to_month_end",
    "is_month_start",
    "is_month_end",
]

# Features derived from the target variables (revenue / cogs).
_TARGET_DERIVED = [
    "lag_1d_revenue",
    "lag_7d_revenue",
    "lag_14d_revenue",
    "lag_28d_revenue",
    "lag_1d_cogs",
    "roll_mean_7d_revenue",
    "roll_mean_28d_revenue",
    "roll_std_7d_revenue",
    "roll_std_28d_revenue",
]


def feature_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c not in ("sales_date", "revenue", "cogs")]


def _recompute_target_features(df: pd.DataFrame) -> pd.DataFrame:
    """Recompute revenue/COGS lags and rolling statistics.

    Mirrors the SQL window functions in ``mart_forecast_daily_modeling.sql``.
    """
    df = df.copy()
    df = df.sort_values("sales_date").reset_index(drop=True)

    df["lag_1d_revenue"] = df["revenue"].shift(1)
    df["lag_7d_revenue"] = df["revenue"].shift(7)
    df["lag_14d_revenue"] = df["revenue"].shift(14)
    df["lag_28d_revenue"] = df["revenue"].shift(28)
    df["lag_1d_cogs"] = df["cogs"].shift(1)

    df["roll_mean_7d_revenue"] = df["lag_1d_revenue"].rolling(window=7, min_periods=1).mean()
    df["roll_mean_28d_revenue"] = df["lag_1d_revenue"].rolling(window=28, min_periods=1).mean()

    df["roll_std_7d_revenue"] = df["lag_1d_revenue"].rolling(window=7, min_periods=2).std()
    df["roll_std_28d_revenue"] = df["lag_1d_revenue"].rolling(window=28, min_periods=2).std()

    return df


def _prepare_future_frame(
    history: pd.DataFrame,
    scaffold: pd.DataFrame,
) -> pd.DataFrame:
    """Build the future slice with calendar features and ffill exogenous vars."""
    future = scaffold[["date"]].copy()
    future = future.rename(columns={"date": "sales_date"})
    future["sales_date"] = pd.to_datetime(future["sales_date"])

    future["year"] = future["sales_date"].dt.year
    future["month"] = future["sales_date"].dt.month
    future["quarter"] = future["sales_date"].dt.quarter
    future["day_of_week"] = future["sales_date"].dt.dayofweek
    future["is_weekend"] = future["day_of_week"].isin([5, 6]).astype(int)
    future["day_of_month"] = future["sales_date"].dt.day
    next_month = future["sales_date"] + pd.offsets.MonthBegin(1)
    future["days_to_month_end"] = (next_month - future["sales_date"]).dt.days
    future["is_month_start"] = (future["day_of_month"] <= 3).astype(int)
    future["is_month_end"] = (future["day_of_month"] > 28).astype(int)

    exogenous_cols = [
        c
        for c in history.columns
        if c not in ("sales_date", "revenue", "cogs")
        and c not in CALENDAR_FEATURES
        and c not in _TARGET_DERIVED
    ]

    last_row = history.iloc[[-1]]
    for col in exogenous_cols:
        future[col] = float(last_row[col].iloc[0])

    for col in _TARGET_DERIVED:
        if col in history.columns:
            future[col] = float(last_row[col].iloc[0])

    future["revenue"] = np.nan
    future["cogs"] = np.nan

    return future


def recursive_forecast(
    forecaster: BaseForecaster,
    history: pd.DataFrame,
    scaffold: pd.DataFrame,
    feature_cols: list[str],
) -> pd.DataFrame:
    """Generate multi-step forecast by recursively predicting targets.

    Exogenous features are forward-filled from the last historical row.
    Target-derived lags / rolling statistics are recomputed after each step.
    """
    history = history.copy()
    future = _prepare_future_frame(history, scaffold)

    combined = pd.concat([history, future], ignore_index=True)
    combined = combined.sort_values("sales_date").reset_index(drop=True)
    history_len = len(history)

    for i in range(len(future)):
        idx = history_len + i
        combined = _recompute_target_features(combined)

        X = combined[feature_cols].iloc[[idx]]
        pred_rev, pred_cogs = forecaster.predict(X)

        combined.at[idx, "revenue"] = max(0.0, float(pred_rev[0]))
        combined.at[idx, "cogs"] = max(0.0, float(pred_cogs[0]))

    predictions = combined.iloc[history_len:][["sales_date", "revenue", "cogs"]].copy()
    predictions = predictions.rename(columns={"sales_date": "date"})
    return predictions
