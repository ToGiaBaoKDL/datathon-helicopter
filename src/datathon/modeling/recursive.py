"""Recursive multi-step forecasting helpers.

Target-derived features (lags, rolling stats, EMA, trend) are recomputed
incrementally after each prediction step to keep the forecast self-contained.
Calendar features and seasonal baselines are derived directly from the date
and are perfectly known in advance — no leakage risk.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from datathon.modeling.forecasters.base import BaseForecaster

# ---------------------------------------------------------------------------
# Feature categorisation
# ---------------------------------------------------------------------------

CALENDAR_FEATURES = [
    "day_of_week",
    "day_of_month",
    "days_to_month_end",
    "days_to_quarter_end",
    "day_of_week_sin",
    "day_of_week_cos",
    "day_of_year_sin",
    "day_of_year_cos",
    "month_sin",
    "month_cos",
    "days_since_2019",
    "promo_month_day_count",
    "promo_month_prob",
    "promo_month_avg_discount",
    "is_sale_season",
    "sale_rank",
    "days_to_next_sale",
    "days_since_last_sale",
    "is_peak_season",
    "peak_proximity",
    "is_month_start_window",
    "is_month_end_window",
    "hist_avg_revenue_dow",
    "hist_avg_cogs_dow",
    "hist_avg_revenue_month",
    "hist_avg_cogs_month",
    "hist_avg_revenue_dom",
    "hist_avg_cogs_dom",
    "overall_avg_revenue",
    "overall_avg_cogs",
    "revenue_baseline",
    "cogs_baseline",
    "log_revenue_baseline",
    "log_cogs_baseline",
    "month_sin",
    "month_cos",
    "is_month_end_window",
    "is_month_start_window",
    "is_pay_day",
]

_TARGET_DERIVED = [
    "lag_1d_revenue",
    "lag_2d_revenue",
    "lag_3d_revenue",
    "lag_7d_revenue",
    "lag_14d_revenue",
    "lag_28d_revenue",
    "lag_90d_revenue",
    "lag_180d_revenue",
    "lag_365d_revenue",
    "lag_730d_revenue",
    "lag_1d_rev_wow_growth",
    "lag_1d_rev_mom_growth",
    "lag_1d_rev_yoy_growth",
    "rev_wow_acceleration",
    "rev_mom_acceleration",
    "rev_yoy_acceleration",
    "lag_1d_cogs",
    "lag_7d_cogs",
    "lag_28d_cogs",
    "lag_365d_cogs",
    "lag_730d_cogs",
    "lag_1d_rev_residual",
    "lag_7d_rev_residual",
    "lag_1d_cogs_residual",
    "lag_7d_cogs_residual",
    "roll_mean_7d_revenue",
    "roll_mean_28d_revenue",
    "roll_std_7d_revenue",
    "roll_std_28d_revenue",
    "roll_std_365d_revenue",
    "roll_mean_7d_cogs",
    "roll_mean_28d_cogs",
    "roll_std_28d_cogs",
    "roll_mean_7d_cogs_ratio",
    "roll_mean_28d_cogs_ratio",
    "roll_std_28d_cogs_ratio",
    "lag_1d_cogs_ratio",
    "revenue_diff_7d",
    "cogs_diff_7d",
]

_PYTHON_ONLY_FEATURES = [
    "ema_7d_revenue",
    "ema_28d_revenue",
    "ema_7d_cogs",
    "ema_28d_cogs",
    "trend_7d_revenue",
    "trend_14d_revenue",
    "trend_28d_revenue",
    "ewm_vol_7d_revenue",
    "cogs_ratio_trend_28d",
]

# Features that are perfectly known in advance (calendar / seasonal / profile).
# Used by direct-forecast mode to avoid recursive error accumulation.
_STATIC_FEATURES = {
    "day_of_week",
    "day_of_month",
    "month",
    "days_to_month_end",
    "days_to_quarter_end",
    "day_of_week_sin",
    "day_of_week_cos",
    "day_of_year_sin",
    "day_of_year_cos",
    "days_since_2019",
    "promo_month_day_count",
    "promo_month_prob",
    "promo_month_avg_discount",
    "is_sale_season",
    "sale_rank",
    "days_to_next_sale",
    "days_since_last_sale",
    "is_peak_season",
    "peak_proximity",
    "hist_avg_revenue_dow",
    "hist_avg_cogs_dow",
    "hist_avg_revenue_month",
    "hist_avg_cogs_month",
    "hist_avg_revenue_dom",
    "hist_avg_cogs_dom",
    "overall_avg_revenue",
    "overall_avg_cogs",
    "revenue_baseline",
    "cogs_baseline",
    "log_revenue_baseline",
    "log_cogs_baseline",
    "month_sin",
    "month_cos",
    "is_month_end_window",
    "is_month_start_window",
    "is_pay_day",
    # Daily promo intensity (known-in-advance for future dates)
    "promo_count",
    "promo_max_discount",
    "promo_mean_discount",
    "promo_max_min_order_value",
    "promo_stackable_count",
    "is_promo",
}

_META_COLUMNS = {
    "sales_date",
    "revenue",
    "cogs",
    "cogs_ratio",
    "revenue_residual",
    "cogs_residual",
    "naive_revenue_residual",
    "naive_cogs_residual",
    "prophet_revenue_baseline",
    "prophet_cogs_baseline",
    "predicted_revenue",
    "month",
    "day_of_year",
    "order_count",
    "units_sold",
    "sessions",
}

_EMA_ALPHA = {7: 2.0 / 8.0, 28: 2.0 / 29.0}

_SALE_SEASONS = [
    (1, 30, 30, 1),
    (3, 18, 30, 2),
    (6, 23, 29, 3),
    (7, 30, 34, 5),
    (8, 30, 32, 4),
    (11, 18, 45, 6),
]


def _get_sale_windows(years: range) -> list[tuple[pd.Timestamp, pd.Timestamp, int]]:
    windows = []
    for year in years:
        for month, start_day, duration, rank in _SALE_SEASONS:
            try:
                start = pd.Timestamp(year=year, month=month, day=start_day)
            except ValueError:
                start = pd.Timestamp(year=year, month=month, day=1) + pd.offsets.MonthEnd(0)
            end = start + pd.Timedelta(days=duration - 1)
            windows.append((start, end, rank))
    return windows


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def feature_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c not in _META_COLUMNS]


def _ensure_columns(df: pd.DataFrame, cols: list[str]) -> None:
    for col in cols:
        if col not in df.columns:
            df[col] = np.nan


def _ema_next(alpha: float, prev_value: float, prev_ema: float | None) -> float:
    if pd.isna(prev_value):
        return np.nan
    if prev_ema is None or pd.isna(prev_ema):
        return prev_value
    return alpha * prev_value + (1 - alpha) * prev_ema


def _linear_slope(series: pd.Series | np.ndarray) -> float:
    if isinstance(series, pd.Series):
        valid = series.dropna()
        if len(valid) < 2:
            return np.nan
        x = np.asarray(valid.index, dtype=float)
        y = np.asarray(valid.values, dtype=float)
    else:
        arr = np.asarray(series, dtype=float)
        mask = ~np.isnan(arr)
        if mask.sum() < 2:
            return np.nan
        x = np.arange(len(arr), dtype=float)[mask]
        y = arr[mask]
    return np.polyfit(x, y, 1)[0]


def _backfill_historical_features(history: pd.DataFrame) -> None:
    """Compute Python-only features for historical rows.

    Uses the *same* recursive formulas as :func:`_update_row_features` so
    historical values and future incremental updates are perfectly consistent.
    All values are shifted by 1 to align with the recursive convention
    (value at *t* depends on data up to *t-1*).
    """
    rev = history["revenue"].to_numpy(dtype=float)
    cogs = history["cogs"].to_numpy(dtype=float)
    n = len(rev)

    # ---- EMA (revenue & COGS) ----
    for span in (7, 28):
        alpha = _EMA_ALPHA[span]
        ema_rev = np.empty(n, dtype=float)
        ema_cogs = np.empty(n, dtype=float)
        ema_rev[0] = rev[0]
        ema_cogs[0] = cogs[0]
        for i in range(1, n):
            ema_rev[i] = _ema_next(alpha, rev[i], ema_rev[i - 1])
            ema_cogs[i] = _ema_next(alpha, cogs[i], ema_cogs[i - 1])
        ema_rev_rolled = np.roll(ema_rev, 1)
        ema_rev_rolled[0] = np.nan
        history[f"ema_{span}d_revenue"] = ema_rev_rolled
        ema_cogs_rolled = np.roll(ema_cogs, 1)
        ema_cogs_rolled[0] = np.nan
        history[f"ema_{span}d_cogs"] = ema_cogs_rolled

    # ---- Trend slopes (linear regression on recent values) ----
    for win in (7, 14, 28):
        slope = np.empty(n, dtype=float)
        slope[:] = np.nan
        for i in range(1, n):
            window = history["revenue"].iloc[max(0, i - win) : i]
            slope[i] = _linear_slope(window)
        history[f"trend_{win}d_revenue"] = slope

    # ---- COGS ratio trend ----
    if "cogs_ratio" in history.columns:
        cr_slope = np.empty(n, dtype=float)
        cr_slope[:] = np.nan
        for i in range(1, n):
            cr_window = history["cogs_ratio"].iloc[max(0, i - 28) : i]
            cr_slope[i] = _linear_slope(cr_window)
        history["cogs_ratio_trend_28d"] = cr_slope

    # ---- EWM volatility (EMA of squared deviation from EMA-7) ----
    alpha7 = _EMA_ALPHA[7]
    ema7 = np.empty(n, dtype=float)
    ema7[0] = rev[0]
    for i in range(1, n):
        ema7[i] = _ema_next(alpha7, rev[i], ema7[i - 1])
    sq_dev = (rev - ema7) ** 2
    vol = np.empty(n, dtype=float)
    vol[0] = sq_dev[0]
    for i in range(1, n):
        vol[i] = _ema_next(alpha7, sq_dev[i], vol[i - 1])
    vol_rolled = np.roll(vol, 1)
    vol_rolled[0] = np.nan
    history["ewm_vol_7d_revenue"] = vol_rolled


# ---------------------------------------------------------------------------
# Core update logic (O(window) per step)
# ---------------------------------------------------------------------------


def _update_row_features(combined: pd.DataFrame, idx: int) -> None:
    rev = combined["revenue"]
    cogs = combined["cogs"]

    # -- Lags (revenue)
    combined.at[idx, "lag_1d_revenue"] = rev.iloc[idx - 1] if idx >= 1 else np.nan
    combined.at[idx, "lag_2d_revenue"] = rev.iloc[idx - 2] if idx >= 2 else np.nan
    combined.at[idx, "lag_3d_revenue"] = rev.iloc[idx - 3] if idx >= 3 else np.nan
    combined.at[idx, "lag_7d_revenue"] = rev.iloc[idx - 7] if idx >= 7 else np.nan
    combined.at[idx, "lag_14d_revenue"] = rev.iloc[idx - 14] if idx >= 14 else np.nan
    combined.at[idx, "lag_28d_revenue"] = rev.iloc[idx - 28] if idx >= 28 else np.nan
    combined.at[idx, "lag_90d_revenue"] = rev.iloc[idx - 90] if idx >= 90 else np.nan
    combined.at[idx, "lag_180d_revenue"] = rev.iloc[idx - 180] if idx >= 180 else np.nan
    combined.at[idx, "lag_365d_revenue"] = rev.iloc[idx - 365] if idx >= 365 else np.nan
    combined.at[idx, "lag_730d_revenue"] = rev.iloc[idx - 730] if idx >= 730 else np.nan

    # -- Lags (COGS)
    combined.at[idx, "lag_1d_cogs"] = cogs.iloc[idx - 1] if idx >= 1 else np.nan
    combined.at[idx, "lag_7d_cogs"] = cogs.iloc[idx - 7] if idx >= 7 else np.nan
    combined.at[idx, "lag_28d_cogs"] = cogs.iloc[idx - 28] if idx >= 28 else np.nan
    combined.at[idx, "lag_365d_cogs"] = cogs.iloc[idx - 365] if idx >= 365 else np.nan
    combined.at[idx, "lag_730d_cogs"] = cogs.iloc[idx - 730] if idx >= 730 else np.nan

    # -- Lagged residuals (1d and 7d only; 2d/3d pruned as near-zero PACF)
    for lag, offset in ((1, 1), (7, 7)):
        rcol = f"lag_{lag}d_rev_residual"
        ccol = f"lag_{lag}d_cogs_residual"
        if rcol in combined.columns:
            combined.at[idx, rcol] = (
                combined["revenue_residual"].iloc[idx - offset] if idx >= offset else np.nan
            )
        if ccol in combined.columns:
            combined.at[idx, ccol] = (
                combined["cogs_residual"].iloc[idx - offset] if idx >= offset else np.nan
            )

    # -- First-difference momentum (1d vs 7d)
    if "revenue_diff_7d" in combined.columns:
        lag_1d_rev = combined.at[idx, "lag_1d_revenue"]
        lag_7d_rev = combined.at[idx, "lag_7d_revenue"]
        if pd.notna(lag_1d_rev) and pd.notna(lag_7d_rev):
            combined.at[idx, "revenue_diff_7d"] = float(lag_1d_rev - lag_7d_rev)
        else:
            combined.at[idx, "revenue_diff_7d"] = np.nan
    if "cogs_diff_7d" in combined.columns:
        lag_1d_cogs_val = combined.at[idx, "lag_1d_cogs"]
        lag_7d_cogs_val = combined.at[idx, "lag_7d_cogs"]
        if pd.notna(lag_1d_cogs_val) and pd.notna(lag_7d_cogs_val):
            combined.at[idx, "cogs_diff_7d"] = float(lag_1d_cogs_val - lag_7d_cogs_val)
        else:
            combined.at[idx, "cogs_diff_7d"] = np.nan

    # -- Growth ratios (lag_8d / lag_29d computed inline, not materialised)
    lag_1d = combined.at[idx, "lag_1d_revenue"]
    lag_8d = rev.iloc[idx - 8] if idx >= 8 else np.nan
    lag_29d = rev.iloc[idx - 29] if idx >= 29 else np.nan
    lag_365d = combined.at[idx, "lag_365d_revenue"]

    wow = (lag_1d / lag_8d - 1) if pd.notna(lag_8d) and lag_8d != 0 else np.nan
    mom = (lag_1d / lag_29d - 1) if pd.notna(lag_29d) and lag_29d != 0 else np.nan
    yoy = (lag_1d / lag_365d - 1) if pd.notna(lag_365d) and lag_365d != 0 else np.nan

    combined.at[idx, "lag_1d_rev_wow_growth"] = wow
    combined.at[idx, "lag_1d_rev_mom_growth"] = mom
    combined.at[idx, "lag_1d_rev_yoy_growth"] = yoy

    # -- Acceleration
    prev_wow = combined.at[idx - 1, "lag_1d_rev_wow_growth"] if idx >= 1 else np.nan
    prev_mom = combined.at[idx - 1, "lag_1d_rev_mom_growth"] if idx >= 1 else np.nan
    prev_yoy = combined.at[idx - 1, "lag_1d_rev_yoy_growth"] if idx >= 1 else np.nan
    combined.at[idx, "rev_wow_acceleration"] = wow - prev_wow
    combined.at[idx, "rev_mom_acceleration"] = mom - prev_mom
    combined.at[idx, "rev_yoy_acceleration"] = yoy - prev_yoy

    # -- Rolling windows (revenue)
    win7 = rev.iloc[max(0, idx - 7) : idx].to_numpy()
    win28 = rev.iloc[max(0, idx - 28) : idx].to_numpy()
    win365 = rev.iloc[max(0, idx - 365) : idx].to_numpy()

    combined.at[idx, "roll_mean_7d_revenue"] = float(np.nanmean(win7)) if len(win7) else np.nan
    combined.at[idx, "roll_mean_28d_revenue"] = float(np.nanmean(win28)) if len(win28) else np.nan
    combined.at[idx, "roll_mean_365d_revenue"] = (
        float(np.nanmean(win365)) if len(win365) else np.nan
    )
    combined.at[idx, "roll_std_7d_revenue"] = (
        float(np.nanstd(win7, ddof=1)) if np.count_nonzero(~np.isnan(win7)) >= 2 else np.nan
    )
    combined.at[idx, "roll_std_28d_revenue"] = (
        float(np.nanstd(win28, ddof=1)) if np.count_nonzero(~np.isnan(win28)) >= 2 else np.nan
    )
    combined.at[idx, "roll_std_365d_revenue"] = (
        float(np.nanstd(win365, ddof=1)) if np.count_nonzero(~np.isnan(win365)) >= 2 else np.nan
    )

    # -- Rolling windows (COGS)
    cogs_win7 = cogs.iloc[max(0, idx - 7) : idx].to_numpy()
    cogs_win28 = cogs.iloc[max(0, idx - 28) : idx].to_numpy()
    combined.at[idx, "roll_mean_7d_cogs"] = (
        float(np.nanmean(cogs_win7)) if len(cogs_win7) else np.nan
    )
    combined.at[idx, "roll_mean_28d_cogs"] = (
        float(np.nanmean(cogs_win28)) if len(cogs_win28) else np.nan
    )
    combined.at[idx, "roll_std_28d_cogs"] = (
        float(np.nanstd(cogs_win28, ddof=1))
        if np.count_nonzero(~np.isnan(cogs_win28)) >= 2
        else np.nan
    )

    # -- COGS ratio rolling
    if "lag_1d_cogs_ratio" in combined.columns:
        cogs_ratio_series = combined["cogs_ratio"]
        combined.at[idx, "lag_1d_cogs_ratio"] = (
            cogs_ratio_series.iloc[idx - 1] if idx >= 1 else np.nan
        )
        cr_win7 = cogs_ratio_series.iloc[max(0, idx - 7) : idx].to_numpy()
        cr_win28 = cogs_ratio_series.iloc[max(0, idx - 28) : idx].to_numpy()
        combined.at[idx, "roll_mean_7d_cogs_ratio"] = (
            float(np.nanmean(cr_win7)) if len(cr_win7) and not np.all(np.isnan(cr_win7)) else np.nan
        )
        combined.at[idx, "roll_mean_28d_cogs_ratio"] = (
            float(np.nanmean(cr_win28))
            if len(cr_win28) and not np.all(np.isnan(cr_win28))
            else np.nan
        )
        combined.at[idx, "roll_std_28d_cogs_ratio"] = (
            float(np.nanstd(cr_win28, ddof=1))
            if np.count_nonzero(~np.isnan(cr_win28)) >= 2
            else np.nan
        )

    if "cogs_ratio_trend_28d" in combined.columns:
        cr_series = combined["cogs_ratio"]
        combined.at[idx, "cogs_ratio_trend_28d"] = _linear_slope(
            cr_series.iloc[max(0, idx - 28) : idx]
        )

    # -- EMA (revenue, COGS, residuals)
    prev_rev = rev.iloc[idx - 1] if idx >= 1 else np.nan
    prev_cogs = cogs.iloc[idx - 1] if idx >= 1 else np.nan

    for span in (7, 28):
        alpha = _EMA_ALPHA[span]
        ema_rev_col = f"ema_{span}d_revenue"
        ema_cogs_col = f"ema_{span}d_cogs"

        if ema_rev_col in combined.columns:
            prev_ema = combined[ema_rev_col].iloc[idx - 1] if idx >= 1 else None
            combined.at[idx, ema_rev_col] = _ema_next(alpha, prev_rev, prev_ema)

        if ema_cogs_col in combined.columns:
            prev_ema = combined[ema_cogs_col].iloc[idx - 1] if idx >= 1 else None
            combined.at[idx, ema_cogs_col] = _ema_next(alpha, prev_cogs, prev_ema)

    # -- Trend slopes (linear regression on recent predicted values)
    if "trend_7d_revenue" in combined.columns:
        combined.at[idx, "trend_7d_revenue"] = _linear_slope(rev.iloc[max(0, idx - 7) : idx])
    if "trend_14d_revenue" in combined.columns:
        combined.at[idx, "trend_14d_revenue"] = _linear_slope(rev.iloc[max(0, idx - 14) : idx])
    if "trend_28d_revenue" in combined.columns:
        combined.at[idx, "trend_28d_revenue"] = _linear_slope(rev.iloc[max(0, idx - 28) : idx])

    # -- Exponentially-weighted volatility (squared deviation from EMA)
    if "ewm_vol_7d_revenue" in combined.columns:
        prev_vol = combined["ewm_vol_7d_revenue"].iloc[idx - 1] if idx >= 1 else None
        prev_ema = combined["ema_7d_revenue"].iloc[idx - 1] if idx >= 1 else None
        if pd.notna(prev_rev) and pd.notna(prev_ema):
            sq_dev = (prev_rev - prev_ema) ** 2
            combined.at[idx, "ewm_vol_7d_revenue"] = _ema_next(_EMA_ALPHA[7], sq_dev, prev_vol)
        else:
            combined.at[idx, "ewm_vol_7d_revenue"] = np.nan

    # -- COGS ratio sync
    if "cogs_ratio" in combined.columns:
        rev_val = combined.at[idx, "revenue"]
        cogs_val = combined.at[idx, "cogs"]
        combined.at[idx, "cogs_ratio"] = (
            cogs_val / rev_val if pd.notna(rev_val) and rev_val != 0 else np.nan
        )


# ---------------------------------------------------------------------------
# Future frame preparation
# ---------------------------------------------------------------------------


def _prepare_future_frame(
    history: pd.DataFrame,
    scaffold: pd.DataFrame,
) -> pd.DataFrame:
    future = scaffold[["date"]].copy()
    future = future.rename(columns={"date": "sales_date"})
    future["sales_date"] = pd.to_datetime(future["sales_date"])

    _month = future["sales_date"].dt.month
    future["month"] = _month
    future["day_of_week"] = future["sales_date"].dt.dayofweek
    future["day_of_month"] = future["sales_date"].dt.day
    _day_of_year = future["sales_date"].dt.dayofyear
    future["day_of_year"] = _day_of_year
    next_month = future["sales_date"] + pd.offsets.MonthBegin(1)
    future["days_to_month_end"] = (next_month - future["sales_date"]).dt.days

    quarter_end = future["sales_date"] + pd.offsets.QuarterEnd(0)
    future["days_to_quarter_end"] = (quarter_end - future["sales_date"]).dt.days

    future["day_of_week_sin"] = np.sin(2 * np.pi * future["day_of_week"] / 7)
    future["day_of_week_cos"] = np.cos(2 * np.pi * future["day_of_week"] / 7)
    _days_in_year = future["sales_date"].apply(lambda d: 366 if d.is_leap_year else 365)
    future["day_of_year_sin"] = np.sin(2 * np.pi * _day_of_year / _days_in_year)
    future["day_of_year_cos"] = np.cos(2 * np.pi * _day_of_year / _days_in_year)
    future["month_sin"] = np.sin(2 * np.pi * future["month"] / 12)
    future["month_cos"] = np.cos(2 * np.pi * future["month"] / 12)

    future["days_since_2019"] = (future["sales_date"] - pd.Timestamp("2019-01-01")).dt.days
    future["is_month_start_window"] = (future["day_of_month"] <= 3).astype(int)
    future["is_month_end_window"] = (future["days_to_month_end"] <= 4).astype(int)
    future["is_pay_day"] = ((future["day_of_month"] >= 25) | (future["day_of_month"] <= 5)).astype(
        int
    )

    # Seasonal baseline (known-in-advance)
    if all(
        c in history.columns
        for c in (
            "hist_avg_revenue_dow",
            "hist_avg_revenue_month",
            "overall_avg_revenue",
            "hist_avg_cogs_dow",
            "hist_avg_cogs_month",
            "overall_avg_cogs",
        )
    ):
        dow_rev_map = history.groupby("day_of_week")["hist_avg_revenue_dow"].first()
        month_rev_map = history.groupby("month")["hist_avg_revenue_month"].first()
        dow_cogs_map = history.groupby("day_of_week")["hist_avg_cogs_dow"].first()
        month_cogs_map = history.groupby("month")["hist_avg_cogs_month"].first()
        overall_rev = history["overall_avg_revenue"].iloc[0]
        overall_cogs = history["overall_avg_cogs"].iloc[0]

        future["hist_avg_revenue_dow"] = future["day_of_week"].map(dow_rev_map)
        future["hist_avg_revenue_month"] = future["month"].map(month_rev_map)
        future["hist_avg_cogs_dow"] = future["day_of_week"].map(dow_cogs_map)
        future["hist_avg_cogs_month"] = future["month"].map(month_cogs_map)
        future["overall_avg_revenue"] = overall_rev
        future["overall_avg_cogs"] = overall_cogs

        if "hist_avg_revenue_dom" in history.columns:
            dom_rev_map = history.groupby("day_of_month")["hist_avg_revenue_dom"].first()
            dom_cogs_map = history.groupby("day_of_month")["hist_avg_cogs_dom"].first()
            future["hist_avg_revenue_dom"] = future["day_of_month"].map(dom_rev_map)
            future["hist_avg_cogs_dom"] = future["day_of_month"].map(dom_cogs_map)

        future["revenue_baseline"] = (
            future["hist_avg_revenue_dow"] + future["hist_avg_revenue_month"] - overall_rev
        )
        future["cogs_baseline"] = (
            future["hist_avg_cogs_dow"] + future["hist_avg_cogs_month"] - overall_cogs
        )

        if "log_revenue_baseline" in history.columns:
            future["log_revenue_baseline"] = np.log1p(future["revenue_baseline"].clip(lower=0))
        if "log_cogs_baseline" in history.columns:
            future["log_cogs_baseline"] = np.log1p(future["cogs_baseline"].clip(lower=0))

    # Prophet baseline (overrides additive decomposition when enabled)
    if "prophet_revenue_baseline" in history.columns:
        from datathon.modeling.prophet_baseline import ProphetBaseline
        from datathon.utils.paths import models_dir

        cache_path = models_dir() / "prophet_baseline.pkl"
        if cache_path.exists():
            pb = ProphetBaseline.load(cache_path)
            prophet_future = pb.predict_future(scaffold)
            future = future.merge(prophet_future, left_on="sales_date", right_on="date", how="left")
            future = future.drop(columns=["date"])
            if getattr(pb, "_log_transform", False):
                future["log_revenue_baseline"] = future["prophet_revenue_baseline"]
                future["log_cogs_baseline"] = future["prophet_cogs_baseline"]
                future["revenue_baseline"] = np.expm1(future["prophet_revenue_baseline"])
                future["cogs_baseline"] = np.expm1(future["prophet_cogs_baseline"])
            else:
                future["revenue_baseline"] = future["prophet_revenue_baseline"]
                future["cogs_baseline"] = future["prophet_cogs_baseline"]

    # Promo profiles (known-in-advance)
    if "promo_month_day_count" in history.columns:
        promo_count_map = history.groupby("month")["promo_month_day_count"].first()
        promo_prob_map = history.groupby("month")["promo_month_prob"].first()
        promo_discount_map = history.groupby("month")["promo_month_avg_discount"].first()
        future["promo_month_day_count"] = future["month"].map(promo_count_map).fillna(0)
        future["promo_month_prob"] = future["month"].map(promo_prob_map).fillna(0)
        future["promo_month_avg_discount"] = future["month"].map(promo_discount_map).fillna(0)

    # Sale season features (known-in-advance domain knowledge)
    if "is_sale_season" in history.columns:
        _min_year = int(future["sales_date"].dt.year.min()) - 1
        _max_year = int(future["sales_date"].dt.year.max()) + 2
        sale_windows = _get_sale_windows(range(_min_year, _max_year + 1))

        # Flatten all sale dates into a lookup set
        sale_dates_set = set()
        sale_date_to_rank = {}
        for start, end, rank in sale_windows:
            for d in pd.date_range(start, end, freq="D"):
                sale_dates_set.add(d)
                sale_date_to_rank[d] = max(sale_date_to_rank.get(d, 0), rank)

        future_dates = future["sales_date"].reset_index(drop=True)
        future["is_sale_season"] = future_dates.isin(sale_dates_set).astype(int)
        future["sale_rank"] = future_dates.map(sale_date_to_rank).fillna(0).astype(int)

        # days_to_next_sale & days_since_last_sale
        sale_dates_sorted = sorted(sale_dates_set)
        days_to_next = []
        days_since_last = []
        for d in future_dates:
            if d in sale_dates_set:
                days_to_next.append(0)
                days_since_last.append(0)
            else:
                next_dates = [sd for sd in sale_dates_sorted if sd > d]
                if next_dates:
                    days_to_next.append(int((next_dates[0] - d).days))
                else:
                    days_to_next.append(999)
                prev_dates = [sd for sd in sale_dates_sorted if sd < d]
                if prev_dates:
                    days_since_last.append(int((d - prev_dates[-1]).days))
                else:
                    days_since_last.append(999)
        future["days_to_next_sale"] = days_to_next
        future["days_since_last_sale"] = days_since_last

    # Peak season features (known-in-advance)
    if "is_peak_season" in history.columns:
        future["is_peak_season"] = future["month"].isin([4, 5, 11]).astype(int)

        _min_year = int(future["sales_date"].dt.year.min()) - 1
        _max_year = int(future["sales_date"].dt.year.max()) + 2
        peak_dates_list = []
        for year in range(_min_year, _max_year + 1):
            for m in (4, 5, 11):
                peak_dates_list.append(pd.Timestamp(year, m, 1))
            peak_dates_idx = pd.DatetimeIndex(peak_dates_list)

            peak_proximity = []
            for d in future["sales_date"]:
                distances = np.abs((peak_dates_idx - d).days)
                peak_proximity.append(1.0 / (1.0 + int(distances.min())))
        future["peak_proximity"] = peak_proximity

    # Forward-fill any remaining exogenous columns.
    # If the scaffold already provides the column (e.g. promo features
    # computed externally for future dates), use those values instead of
    # freezing the last historical observation.
    exogenous_cols = [
        c
        for c in history.columns
        if c not in _META_COLUMNS
        and c not in CALENDAR_FEATURES
        and c not in _TARGET_DERIVED
        and c not in _PYTHON_ONLY_FEATURES
    ]
    last_row = history.iloc[[-1]]
    for col in exogenous_cols:
        if col in scaffold.columns:
            future[col] = scaffold[col].to_numpy()
        else:
            future[col] = float(last_row[col].iloc[0])

    # Seed target-derived columns with last known historical value
    for col in _TARGET_DERIVED:
        if col in history.columns:
            future[col] = float(last_row[col].iloc[0])

    # Ensure Python-only feature columns exist
    _ensure_columns(future, _PYTHON_ONLY_FEATURES)

    # Meta placeholders
    future["revenue"] = np.nan
    future["cogs"] = np.nan
    for col in (
        "cogs_ratio",
        "revenue_residual",
        "cogs_residual",
        "predicted_revenue",
    ):
        if col in history.columns:
            future[col] = np.nan

    return future


# ---------------------------------------------------------------------------
# Recursive forecast loop
# ---------------------------------------------------------------------------


def recursive_forecast(
    forecaster: BaseForecaster,
    history: pd.DataFrame,
    scaffold: pd.DataFrame,
    feature_cols: list[str],
    cogs_is_ratio: bool = False,
    target_transform: str = "identity",
    restart_horizon: int | None = None,
) -> pd.DataFrame:
    if target_transform not in ("identity", "residual", "log", "log_residual"):
        raise ValueError(
            f"target_transform must be one of: identity, residual, log, log_residual. "
            f"Got: {target_transform!r}"
        )

    history = history.copy()
    _ensure_columns(history, _PYTHON_ONLY_FEATURES)
    _backfill_historical_features(history)

    if restart_horizon is None or len(scaffold) <= restart_horizon:
        predictions, _future_slice = _recursive_forecast_single_pass(
            forecaster,
            history,
            scaffold,
            feature_cols,
            cogs_is_ratio,
            target_transform,
        )
        return predictions

    # Restart strategy: predict in chunks to reduce error accumulation.
    # After each chunk, the predicted rows (with all feature columns
    # materialised) are appended back to history so lags/rolling windows
    # are recomputed from real predictions rather than stale seeds.
    all_preds: list[pd.DataFrame] = []
    remaining = scaffold.copy()
    current_history = history.copy()

    while len(remaining) > 0:
        chunk_scaffold = remaining.iloc[:restart_horizon].copy()
        remaining = remaining.iloc[restart_horizon:].copy()

        chunk_pred, chunk_future = _recursive_forecast_single_pass(
            forecaster,
            current_history,
            chunk_scaffold,
            feature_cols,
            cogs_is_ratio,
            target_transform,
        )
        all_preds.append(chunk_pred)

        # Append the fully-materialised future slice back to history.
        current_history = pd.concat([current_history, chunk_future], ignore_index=True)
        current_history = current_history.sort_values("sales_date").reset_index(drop=True)
        _backfill_historical_features(current_history)

    return pd.concat(all_preds, ignore_index=True)


def direct_forecast(
    forecaster: BaseForecaster,
    history: pd.DataFrame,
    scaffold: pd.DataFrame,
    feature_cols: list[str],
    cogs_is_ratio: bool = False,
    target_transform: str = "identity",
) -> pd.DataFrame:
    """Direct forecast: predict all future dates at once using static features only.

    No recursive loop, no lag/rolling updates — eliminates error accumulation
    over long horizons.  Only features in :data:`_STATIC_FEATURES` are used.
    """
    if target_transform not in ("identity", "residual", "log", "log_residual"):
        raise ValueError(
            f"target_transform must be one of: identity, residual, log, log_residual. "
            f"Got: {target_transform!r}"
        )

    future = _prepare_future_frame(history, scaffold)
    static_cols = [c for c in feature_cols if c in _STATIC_FEATURES and c in future.columns]
    if not static_cols:
        raise ValueError(
            "direct_forecast requires at least one static feature. "
            "Check that feature_cols contains known-in-advance features."
        )

    X_future = future[static_cols]
    pred_rev, pred_cogs = forecaster.predict(X_future)
    pred_rev = np.asarray(pred_rev, dtype=float)
    pred_cogs = np.asarray(pred_cogs, dtype=float)

    if target_transform == "residual":
        rev_baseline = future["revenue_baseline"].to_numpy(dtype=float)
        rev_baseline = np.where(np.isnan(rev_baseline), 0.0, rev_baseline)
        rev_val = np.maximum(0.0, rev_baseline + pred_rev)
        if cogs_is_ratio:
            ratio_val = np.clip(pred_cogs, 0.0, 2.0)
            cogs_val = rev_val * ratio_val
        else:
            cogs_baseline = future["cogs_baseline"].to_numpy(dtype=float)
            cogs_baseline = np.where(np.isnan(cogs_baseline), 0.0, cogs_baseline)
            cogs_val = np.maximum(0.0, cogs_baseline + pred_cogs)
    elif target_transform == "log_residual":
        log_rev_baseline = future["log_revenue_baseline"].to_numpy(dtype=float)
        log_rev_baseline = np.where(np.isnan(log_rev_baseline), 0.0, log_rev_baseline)
        rev_val = np.maximum(0.0, np.expm1(log_rev_baseline + pred_rev))
        if cogs_is_ratio:
            ratio_val = np.clip(pred_cogs, 0.0, 2.0)
            cogs_val = rev_val * ratio_val
        else:
            log_cogs_baseline = future["log_cogs_baseline"].to_numpy(dtype=float)
            log_cogs_baseline = np.where(np.isnan(log_cogs_baseline), 0.0, log_cogs_baseline)
            cogs_val = np.maximum(0.0, np.expm1(log_cogs_baseline + pred_cogs))
    elif target_transform == "log":
        rev_val = np.maximum(0.0, np.expm1(pred_rev))
        if cogs_is_ratio:
            ratio_val = np.clip(pred_cogs, 0.0, 2.0)
            cogs_val = rev_val * ratio_val
        else:
            cogs_val = np.maximum(0.0, np.expm1(pred_cogs))
    else:  # identity
        rev_val = np.maximum(0.0, pred_rev)
        if cogs_is_ratio:
            ratio_val = np.clip(pred_cogs, 0.0, 2.0)
            cogs_val = rev_val * ratio_val
        else:
            cogs_val = np.maximum(0.0, pred_cogs)

    predictions = future[["sales_date"]].copy()
    predictions["revenue"] = rev_val
    predictions["cogs"] = cogs_val
    predictions = predictions.rename(columns={"sales_date": "date"})
    return predictions


def _recursive_forecast_single_pass(
    forecaster: BaseForecaster,
    history: pd.DataFrame,
    scaffold: pd.DataFrame,
    feature_cols: list[str],
    cogs_is_ratio: bool,
    target_transform: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Single-pass recursive forecast.

    Returns
    -------
    predictions : DataFrame with columns [date, revenue, cogs]
    future_slice : DataFrame with the fully materialised future rows
                   (all feature columns preserved) so it can be appended
                   back to history in restart mode.
    """
    future = _prepare_future_frame(history, scaffold)
    combined = pd.concat([history, future], ignore_index=True)
    combined = combined.sort_values("sales_date").reset_index(drop=True)
    history_len = len(history)

    for i in range(len(future)):
        idx = history_len + i
        _update_row_features(combined, idx)

        X = combined[feature_cols].iloc[[idx]]
        pred_rev, pred_cogs = forecaster.predict(X)

        if target_transform == "residual":
            rev_baseline = combined.at[idx, "revenue_baseline"]
            rev_baseline = float(rev_baseline) if pd.notna(rev_baseline) else 0.0
            rev_val = max(0.0, rev_baseline + float(pred_rev[0]))

            if cogs_is_ratio:
                ratio_val = max(0.0, min(2.0, float(pred_cogs[0])))
                cogs_val = rev_val * ratio_val
            else:
                cogs_baseline = combined.at[idx, "cogs_baseline"]
                cogs_baseline = float(cogs_baseline) if pd.notna(cogs_baseline) else 0.0
                cogs_val = max(0.0, cogs_baseline + float(pred_cogs[0]))
        elif target_transform == "log_residual":
            log_rev_baseline = combined.at[idx, "log_revenue_baseline"]
            log_rev_baseline = float(log_rev_baseline) if pd.notna(log_rev_baseline) else 0.0
            rev_val = max(0.0, float(np.expm1(log_rev_baseline + pred_rev[0])))

            if cogs_is_ratio:
                ratio_val = max(0.0, min(2.0, float(pred_cogs[0])))
                cogs_val = rev_val * ratio_val
            else:
                log_cogs_baseline = combined.at[idx, "log_cogs_baseline"]
                log_cogs_baseline = float(log_cogs_baseline) if pd.notna(log_cogs_baseline) else 0.0
                cogs_val = max(0.0, float(np.expm1(log_cogs_baseline + pred_cogs[0])))
        elif target_transform == "log":
            rev_val = max(0.0, float(np.expm1(pred_rev[0])))
            if cogs_is_ratio:
                ratio_val = max(0.0, min(2.0, float(pred_cogs[0])))
                cogs_val = rev_val * ratio_val
            else:
                cogs_val = max(0.0, float(np.expm1(pred_cogs[0])))
        else:  # identity
            rev_val = max(0.0, float(pred_rev[0]))
            if cogs_is_ratio:
                ratio_val = max(0.0, min(2.0, float(pred_cogs[0])))
                cogs_val = rev_val * ratio_val
            else:
                cogs_val = max(0.0, float(pred_cogs[0]))

        combined.at[idx, "revenue"] = rev_val
        combined.at[idx, "cogs"] = cogs_val

        if target_transform == "log_residual":
            if "log_revenue_baseline" in combined.columns:
                log_base = (
                    float(combined.at[idx, "log_revenue_baseline"])
                    if pd.notna(combined.at[idx, "log_revenue_baseline"])
                    else 0.0
                )
                combined.at[idx, "revenue_residual"] = np.log1p(rev_val) - log_base
            if "log_cogs_baseline" in combined.columns and not cogs_is_ratio:
                log_base = (
                    float(combined.at[idx, "log_cogs_baseline"])
                    if pd.notna(combined.at[idx, "log_cogs_baseline"])
                    else 0.0
                )
                combined.at[idx, "cogs_residual"] = np.log1p(cogs_val) - log_base
        else:
            if "revenue_baseline" in combined.columns:
                base = (
                    float(combined.at[idx, "revenue_baseline"])
                    if pd.notna(combined.at[idx, "revenue_baseline"])
                    else 0.0
                )
                combined.at[idx, "revenue_residual"] = rev_val - base
            if "cogs_baseline" in combined.columns and not cogs_is_ratio:
                base = (
                    float(combined.at[idx, "cogs_baseline"])
                    if pd.notna(combined.at[idx, "cogs_baseline"])
                    else 0.0
                )
                combined.at[idx, "cogs_residual"] = cogs_val - base

    future_slice = combined.iloc[history_len:].copy()
    predictions = future_slice[["sales_date", "revenue", "cogs"]].copy()
    predictions = predictions.rename(columns={"sales_date": "date"})
    return predictions, future_slice
