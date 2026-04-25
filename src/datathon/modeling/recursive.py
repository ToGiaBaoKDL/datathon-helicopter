"""Recursive multi-step forecasting helpers."""

from __future__ import annotations

import functools

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
    "day_of_year",
    "week_of_year",
    "days_to_month_end",
    "days_to_quarter_end",
    "is_month_start",
    "is_month_end",
    "is_quarter_end",
    "month_sin",
    "month_cos",
    "day_of_week_sin",
    "day_of_week_cos",
    "day_of_year_sin",
    "day_of_year_cos",
    "week_of_year_sin",
    "week_of_year_cos",
    "days_to_tet",
    "is_pre_tet_rush",
    "is_tet_holiday",
    "is_post_tet",
    "is_reunification_day",
    "is_labor_day",
    "is_national_day",
    "is_decline_era",
    "days_since_2019",
]

# Features derived from the target variables (revenue / cogs).
_TARGET_DERIVED = [
    "lag_1d_revenue",
    "lag_2d_revenue",
    "lag_3d_revenue",
    "lag_7d_revenue",
    "lag_8d_revenue",
    "lag_14d_revenue",
    "lag_28d_revenue",
    "lag_29d_revenue",
    "lag_365d_revenue",
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
    "roll_mean_7d_revenue",
    "roll_mean_28d_revenue",
    "roll_mean_365d_revenue",
    "roll_median_7d_revenue",
    "roll_median_28d_revenue",
    "roll_std_7d_revenue",
    "roll_std_28d_revenue",
    "roll_std_365d_revenue",
    "roll_mean_7d_cogs",
    "roll_mean_28d_cogs",
]


_META_COLUMNS = {
    "sales_date",
    "revenue",
    "cogs",
    "cogs_ratio",
    "revenue_baseline",
    "cogs_baseline",
    "revenue_residual",
    "cogs_residual",
    "tet_date",
}


@functools.lru_cache(maxsize=1)
def _load_tet_dates() -> pd.Series:
    """Load full tet date mapping from the DuckDB warehouse (seeds schema)."""
    from datathon.utils.duckdb_io import connect
    from datathon.utils.paths import warehouse_path

    with connect(warehouse_path()) as conn:
        df = conn.execute("select year, tet_date from seeds.tet_dates").fetchdf()
    df["tet_date"] = pd.to_datetime(df["tet_date"])
    return df.set_index("year")["tet_date"]


def feature_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c not in _META_COLUMNS]


def _update_row_features(combined: pd.DataFrame, idx: int) -> None:
    """Incrementally update target-derived features for a single row *idx*.

    Avoids the O(n²) cost of recomputing rolling windows across the entire
    DataFrame at every recursive step.
    """
    rev = combined["revenue"]
    cogs = combined["cogs"]

    # Lags — revenue
    combined.at[idx, "lag_1d_revenue"] = rev.iloc[idx - 1] if idx >= 1 else np.nan
    combined.at[idx, "lag_2d_revenue"] = rev.iloc[idx - 2] if idx >= 2 else np.nan
    combined.at[idx, "lag_3d_revenue"] = rev.iloc[idx - 3] if idx >= 3 else np.nan
    combined.at[idx, "lag_7d_revenue"] = rev.iloc[idx - 7] if idx >= 7 else np.nan
    combined.at[idx, "lag_14d_revenue"] = rev.iloc[idx - 14] if idx >= 14 else np.nan
    combined.at[idx, "lag_28d_revenue"] = rev.iloc[idx - 28] if idx >= 28 else np.nan
    combined.at[idx, "lag_365d_revenue"] = rev.iloc[idx - 365] if idx >= 365 else np.nan
    combined.at[idx, "lag_8d_revenue"] = rev.iloc[idx - 8] if idx >= 8 else np.nan
    combined.at[idx, "lag_29d_revenue"] = rev.iloc[idx - 29] if idx >= 29 else np.nan

    # Lags — COGS
    combined.at[idx, "lag_1d_cogs"] = cogs.iloc[idx - 1] if idx >= 1 else np.nan
    combined.at[idx, "lag_7d_cogs"] = cogs.iloc[idx - 7] if idx >= 7 else np.nan
    combined.at[idx, "lag_28d_cogs"] = cogs.iloc[idx - 28] if idx >= 28 else np.nan
    combined.at[idx, "lag_365d_cogs"] = cogs.iloc[idx - 365] if idx >= 365 else np.nan

    # Growth ratios
    lag_1d = combined.at[idx, "lag_1d_revenue"]
    lag_8d = combined.at[idx, "lag_8d_revenue"]
    lag_29d = combined.at[idx, "lag_29d_revenue"]
    lag_365d = combined.at[idx, "lag_365d_revenue"]

    wow = (lag_1d / lag_8d - 1) if pd.notna(lag_8d) and lag_8d != 0 else 0.0
    mom = (lag_1d / lag_29d - 1) if pd.notna(lag_29d) and lag_29d != 0 else 0.0
    yoy = (lag_1d / lag_365d - 1) if pd.notna(lag_365d) and lag_365d != 0 else 0.0

    combined.at[idx, "lag_1d_rev_wow_growth"] = wow
    combined.at[idx, "lag_1d_rev_mom_growth"] = mom
    combined.at[idx, "lag_1d_rev_yoy_growth"] = yoy

    # Acceleration: change in growth rate from previous day
    prev_wow = combined.at[idx - 1, "lag_1d_rev_wow_growth"] if idx >= 1 else 0.0
    prev_mom = combined.at[idx - 1, "lag_1d_rev_mom_growth"] if idx >= 1 else 0.0
    prev_yoy = combined.at[idx - 1, "lag_1d_rev_yoy_growth"] if idx >= 1 else 0.0
    combined.at[idx, "rev_wow_acceleration"] = wow - prev_wow
    combined.at[idx, "rev_mom_acceleration"] = mom - prev_mom
    combined.at[idx, "rev_yoy_acceleration"] = yoy - prev_yoy

    # Rolling statistics on lag_1d_revenue == revenue shifted by 1.
    if idx >= 1:
        win7 = rev.iloc[max(0, idx - 7) : idx].to_numpy()
        win28 = rev.iloc[max(0, idx - 28) : idx].to_numpy()
        win365 = rev.iloc[max(0, idx - 365) : idx].to_numpy()

        combined.at[idx, "roll_mean_7d_revenue"] = float(np.mean(win7))
        combined.at[idx, "roll_mean_28d_revenue"] = float(np.mean(win28))
        combined.at[idx, "roll_mean_365d_revenue"] = float(np.mean(win365))

        combined.at[idx, "roll_median_7d_revenue"] = float(np.median(win7))
        combined.at[idx, "roll_median_28d_revenue"] = float(np.median(win28))

        combined.at[idx, "roll_std_7d_revenue"] = (
            float(np.std(win7, ddof=1)) if len(win7) >= 2 else 0.0
        )
        combined.at[idx, "roll_std_28d_revenue"] = (
            float(np.std(win28, ddof=1)) if len(win28) >= 2 else 0.0
        )
        combined.at[idx, "roll_std_365d_revenue"] = (
            float(np.std(win365, ddof=1)) if len(win365) >= 2 else 0.0
        )
    else:
        combined.at[idx, "roll_mean_7d_revenue"] = 0.0
        combined.at[idx, "roll_mean_28d_revenue"] = 0.0
        combined.at[idx, "roll_mean_365d_revenue"] = 0.0
        combined.at[idx, "roll_median_7d_revenue"] = 0.0
        combined.at[idx, "roll_median_28d_revenue"] = 0.0
        combined.at[idx, "roll_std_7d_revenue"] = 0.0
        combined.at[idx, "roll_std_28d_revenue"] = 0.0
        combined.at[idx, "roll_std_365d_revenue"] = 0.0

    # COGS rolling means
    if idx >= 1:
        cogs_win7 = cogs.iloc[max(0, idx - 7) : idx].to_numpy()
        cogs_win28 = cogs.iloc[max(0, idx - 28) : idx].to_numpy()
        combined.at[idx, "roll_mean_7d_cogs"] = float(np.mean(cogs_win7))
        combined.at[idx, "roll_mean_28d_cogs"] = float(np.mean(cogs_win28))
    else:
        combined.at[idx, "roll_mean_7d_cogs"] = 0.0
        combined.at[idx, "roll_mean_28d_cogs"] = 0.0

    # Baseline / residual (lag_365d is the naive YoY forecast)
    if "revenue_baseline" in combined.columns:
        combined.at[idx, "revenue_baseline"] = combined.at[idx, "lag_365d_revenue"]
    if "cogs_baseline" in combined.columns:
        combined.at[idx, "cogs_baseline"] = combined.at[idx, "lag_365d_cogs"]

    # Keep cogs_ratio in sync with absolute cogs when both are present
    if "cogs_ratio" in combined.columns:
        rev_val = combined.at[idx, "revenue"]
        cogs_val = combined.at[idx, "cogs"]
        combined.at[idx, "cogs_ratio"] = (
            cogs_val / rev_val if pd.notna(rev_val) and rev_val != 0 else np.nan
        )


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
    future["day_of_year"] = future["sales_date"].dt.dayofyear
    future["week_of_year"] = future["sales_date"].dt.isocalendar().week.astype(int)
    next_month = future["sales_date"] + pd.offsets.MonthBegin(1)
    future["days_to_month_end"] = (next_month - future["sales_date"]).dt.days
    future["is_month_start"] = (future["day_of_month"] <= 3).astype(int)
    future["is_month_end"] = (future["day_of_month"] > 28).astype(int)

    # Quarter end
    quarter_end = future["sales_date"] + pd.offsets.QuarterEnd(0)
    future["days_to_quarter_end"] = (quarter_end - future["sales_date"]).dt.days
    future["is_quarter_end"] = (future["days_to_quarter_end"] <= 3).astype(int)

    future["month_sin"] = np.sin(2 * np.pi * future["month"] / 12)
    future["month_cos"] = np.cos(2 * np.pi * future["month"] / 12)
    future["day_of_week_sin"] = np.sin(2 * np.pi * future["day_of_week"] / 7)
    future["day_of_week_cos"] = np.cos(2 * np.pi * future["day_of_week"] / 7)
    _days_in_year = future["sales_date"].apply(lambda d: 366 if d.is_leap_year else 365)
    future["day_of_year_sin"] = np.sin(2 * np.pi * future["day_of_year"] / _days_in_year)
    future["day_of_year_cos"] = np.cos(2 * np.pi * future["day_of_year"] / _days_in_year)
    future["week_of_year_sin"] = np.sin(2 * np.pi * future["week_of_year"] / 52)
    future["week_of_year_cos"] = np.cos(2 * np.pi * future["week_of_year"] / 52)

    # Vietnamese holidays
    future["is_reunification_day"] = (
        (future["month"] == 4) & (future["day_of_month"] == 30)
    ).astype(int)
    future["is_labor_day"] = ((future["month"] == 5) & (future["day_of_month"] == 1)).astype(int)
    future["is_national_day"] = ((future["month"] == 9) & (future["day_of_month"] == 2)).astype(int)

    # Structural break era
    future["is_decline_era"] = (future["year"] >= 2019).astype(int)
    future["days_since_2019"] = (future["sales_date"] - pd.Timestamp("2019-01-01")).dt.days

    # Tet features
    tet_map = _load_tet_dates()
    future["tet_date"] = future["year"].map(tet_map)
    future["days_to_tet"] = (future["tet_date"] - future["sales_date"]).dt.days
    future["is_pre_tet_rush"] = (
        (future["days_to_tet"] > 0) & (future["days_to_tet"] <= 21)
    ).astype(int)
    future["is_tet_holiday"] = (
        (future["days_to_tet"] <= 0) & (future["days_to_tet"] >= -6)
    ).astype(int)
    future["is_post_tet"] = ((future["days_to_tet"] < -6) & (future["days_to_tet"] >= -14)).astype(
        int
    )

    exogenous_cols = [
        c
        for c in history.columns
        if c not in _META_COLUMNS and c not in CALENDAR_FEATURES and c not in _TARGET_DERIVED
    ]

    last_row = history.iloc[[-1]]
    for col in exogenous_cols:
        future[col] = float(last_row[col].iloc[0])

    for col in _TARGET_DERIVED:
        if col in history.columns:
            future[col] = float(last_row[col].iloc[0])

    future["revenue"] = np.nan
    future["cogs"] = np.nan
    if "cogs_ratio" in history.columns:
        future["cogs_ratio"] = np.nan
    if "revenue_baseline" in history.columns:
        future["revenue_baseline"] = np.nan
    if "cogs_baseline" in history.columns:
        future["cogs_baseline"] = np.nan
    if "revenue_residual" in history.columns:
        future["revenue_residual"] = np.nan
    if "cogs_residual" in history.columns:
        future["cogs_residual"] = np.nan

    return future


def recursive_forecast(
    forecaster: BaseForecaster,
    history: pd.DataFrame,
    scaffold: pd.DataFrame,
    feature_cols: list[str],
    cogs_is_ratio: bool = False,
    residual_target: bool = False,
) -> pd.DataFrame:
    """Generate multi-step forecast by recursively predicting targets.

    Exogenous features are forward-filled from the last historical row.
    Target-derived lags / rolling statistics are recomputed after each step.

    Parameters
    ----------
    cogs_is_ratio:
        When ``True``, the second model predicts ``cogs / revenue`` instead
        of absolute COGS.  The returned ``cogs`` column is converted back to
        absolute values (``revenue * ratio``).
    residual_target:
        When ``True``, models predict ``revenue_residual`` and
        ``cogs_residual`` instead of raw revenue / COGS.  The returned
        ``revenue`` and ``cogs`` columns are reconstructed as
        ``baseline + predicted_residual``.
    """
    history = history.copy()
    future = _prepare_future_frame(history, scaffold)

    combined = pd.concat([history, future], ignore_index=True)
    combined = combined.sort_values("sales_date").reset_index(drop=True)
    history_len = len(history)

    for i in range(len(future)):
        idx = history_len + i
        _update_row_features(combined, idx)

        X = combined[feature_cols].iloc[[idx]]
        pred_rev, pred_cogs = forecaster.predict(X)

        if residual_target:
            rev_baseline = combined.at[idx, "revenue_baseline"]
            rev_baseline = float(rev_baseline) if pd.notna(rev_baseline) else 0.0
            rev_val = max(0.0, rev_baseline + float(pred_rev[0]))
            combined.at[idx, "revenue"] = rev_val

            if cogs_is_ratio:
                ratio_val = max(0.0, min(2.0, float(pred_cogs[0])))
                combined.at[idx, "cogs_ratio"] = ratio_val
                combined.at[idx, "cogs"] = rev_val * ratio_val
            else:
                cogs_baseline = combined.at[idx, "cogs_baseline"]
                cogs_baseline = float(cogs_baseline) if pd.notna(cogs_baseline) else 0.0
                cogs_val = max(0.0, cogs_baseline + float(pred_cogs[0]))
                combined.at[idx, "cogs"] = cogs_val
        else:
            rev_val = max(0.0, float(pred_rev[0]))
            combined.at[idx, "revenue"] = rev_val

            if cogs_is_ratio:
                ratio_val = max(0.0, min(2.0, float(pred_cogs[0])))
                combined.at[idx, "cogs_ratio"] = ratio_val
                combined.at[idx, "cogs"] = rev_val * ratio_val
            else:
                combined.at[idx, "cogs"] = max(0.0, float(pred_cogs[0]))

    predictions = combined.iloc[history_len:][["sales_date", "revenue", "cogs"]].copy()
    predictions = predictions.rename(columns={"sales_date": "date"})
    return predictions
