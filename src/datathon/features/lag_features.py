from __future__ import annotations

import pandas as pd


def add_revenue_lag_features(frame: pd.DataFrame, lags: list[int]) -> pd.DataFrame:
    output = frame.sort_values("sales_date").copy()
    for lag_days in lags:
        output[f"lag_{lag_days}d_revenue"] = output["revenue"].shift(lag_days)
    return output


def add_revenue_rolling_features(frame: pd.DataFrame, windows: list[int]) -> pd.DataFrame:
    output = frame.sort_values("sales_date").copy()
    for window in windows:
        shifted = output["revenue"].shift(1)
        output[f"roll_mean_{window}d_revenue"] = shifted.rolling(window).mean()
        output[f"roll_std_{window}d_revenue"] = shifted.rolling(window).std()
    return output
