from __future__ import annotations

import numpy as np
import pandas as pd

try:
    from datathon.modeling.forecasters.lightgbm import LightGBMForecaster

    _HAS_LIGHTGBM = True
except ImportError:
    LightGBMForecaster = None  # type: ignore[misc,assignment]
    _HAS_LIGHTGBM = False

import pytest

from datathon.modeling.recursive import recursive_forecast


def _make_synthetic_history(n: int = 400) -> pd.DataFrame:
    """Return a small history DataFrame with log targets."""
    dates = pd.date_range("2022-01-01", periods=n)
    df = pd.DataFrame(
        {
            "sales_date": dates,
            "revenue": np.random.RandomState(42).randint(1_000, 10_000, size=n).astype(float),
            "cogs": np.random.RandomState(43).randint(500, 8_000, size=n).astype(float),
            "day_of_week": dates.dayofweek,
            "days_to_month_end": 30 - dates.day,
            "days_to_quarter_end": 90 - dates.dayofyear % 90,
            "day_of_week_sin": np.sin(2 * np.pi * dates.dayofweek / 7),
            "day_of_week_cos": np.cos(2 * np.pi * dates.dayofweek / 7),
            "day_of_year_sin": np.sin(2 * np.pi * dates.dayofyear / 365),
            "day_of_year_cos": np.cos(2 * np.pi * dates.dayofyear / 365),
            "is_national_day": 0,
            "days_since_2019": (dates - pd.Timestamp("2019-01-01")).days,
            "lag_1d_revenue": np.nan,
            "lag_2d_revenue": np.nan,
            "lag_3d_revenue": np.nan,
            "lag_7d_revenue": np.nan,
            "lag_14d_revenue": np.nan,
            "lag_28d_revenue": np.nan,
            "lag_365d_revenue": np.nan,
            "lag_1d_cogs": np.nan,
            "lag_7d_cogs": np.nan,
            "lag_28d_cogs": np.nan,
            "lag_365d_cogs": np.nan,
            "lag_1d_rev_wow_growth": np.nan,
            "lag_1d_rev_mom_growth": np.nan,
            "lag_1d_rev_yoy_growth": np.nan,
            "rev_wow_acceleration": np.nan,
            "rev_mom_acceleration": np.nan,
            "rev_yoy_acceleration": np.nan,
            "roll_mean_7d_revenue": np.nan,
            "roll_mean_28d_revenue": np.nan,
            "roll_mean_365d_revenue": np.nan,
            "roll_std_7d_revenue": np.nan,
            "roll_std_28d_revenue": np.nan,
            "roll_std_365d_revenue": np.nan,
            "roll_mean_7d_cogs": np.nan,
            "roll_mean_28d_cogs": np.nan,
            "revenue_baseline": np.nan,
            "cogs_baseline": np.nan,
            "revenue_residual": np.nan,
            "cogs_residual": np.nan,
            "log_revenue": np.nan,
            "log_cogs": np.nan,
        }
    )
    return df


@pytest.mark.skipif(not _HAS_LIGHTGBM, reason="lightgbm not installed")
def test_recursive_forecast_log_transform() -> None:
    """Smoke test: log transform reconstructs revenue via expm1."""
    history = _make_synthetic_history(400)
    history["log_revenue"] = np.log1p(history["revenue"])
    history["log_cogs"] = np.log1p(history["cogs"])

    # Simple feature columns for smoke test
    feat_cols = [
        c
        for c in history.columns
        if c
        not in {
            "sales_date",
            "revenue",
            "cogs",
            "cogs_ratio",
            "revenue_baseline",
            "cogs_baseline",
            "revenue_residual",
            "cogs_residual",
            "log_revenue",
            "log_cogs",
        }
    ]

    X = history[feat_cols].fillna(0)
    y_rev = history["log_revenue"]
    y_cogs = history["log_cogs"]

    model = LightGBMForecaster(n_estimators=10, learning_rate=0.1, verbose=-1)
    model.fit(X, y_rev, y_cogs)

    scaffold = pd.DataFrame({"date": pd.date_range("2023-03-01", periods=3)})
    pred = recursive_forecast(
        model,
        history,
        scaffold,
        feat_cols,
        target_transform="log",
    )

    assert len(pred) == 3
    assert (pred["revenue"] >= 0).all()
    assert (pred["cogs"] >= 0).all()
    # All values should be finite
    assert np.isfinite(pred["revenue"]).all()
    assert np.isfinite(pred["cogs"]).all()
