from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from datathon.modeling.recursive import (
    _META_COLUMNS,
    _TARGET_DERIVED,
    CALENDAR_FEATURES,
    _prepare_future_frame,
    _update_row_features,
    feature_columns,
)


def test_feature_columns_excludes_meta() -> None:
    df = pd.DataFrame({c: [1] for c in list(_META_COLUMNS) + ["extra_a", "extra_b"]})
    cols = feature_columns(df)
    assert set(cols) == {"extra_a", "extra_b"}
    for c in _META_COLUMNS:
        assert c not in cols


def test_feature_columns_empty_when_all_meta() -> None:
    df = pd.DataFrame({c: [1] for c in _META_COLUMNS})
    assert feature_columns(df) == []


class TestUpdateRowFeatures:
    """Unit tests for the incremental feature updater used in recursive forecast."""

    def _make_history(self, n: int = 400) -> pd.DataFrame:
        rng = np.random.default_rng(42)
        dates = pd.date_range("2022-01-01", periods=n, freq="D")
        rev = np.cumsum(rng.random(n) * 1000)
        cogs = rev * 0.8
        df = pd.DataFrame(
            {
                "sales_date": dates,
                "revenue": rev,
                "cogs": cogs,
            }
        )
        # Pre-populate all derived columns with NaN / placeholder
        for col in _TARGET_DERIVED:
            df[col] = np.nan
        df["revenue_baseline"] = np.nan
        df["cogs_baseline"] = np.nan
        df["cogs_ratio"] = df["cogs"] / df["revenue"]
        df["revenue_residual"] = np.nan
        df["cogs_residual"] = np.nan
        return df

    def test_lags_populated_correctly(self) -> None:
        df = self._make_history(400)
        idx = 366  # enough history for 365d lag
        _update_row_features(df, idx)

        assert df.at[idx, "lag_1d_revenue"] == df.at[idx - 1, "revenue"]
        assert df.at[idx, "lag_7d_revenue"] == df.at[idx - 7, "revenue"]
        assert df.at[idx, "lag_365d_revenue"] == df.at[idx - 365, "revenue"]
        assert df.at[idx, "lag_1d_cogs"] == df.at[idx - 1, "cogs"]

    def test_lags_before_window_are_nan(self) -> None:
        df = self._make_history(400)
        idx = 5  # not enough for 7d lag
        _update_row_features(df, idx)

        assert pd.isna(df.at[idx, "lag_7d_revenue"])
        assert pd.isna(df.at[idx, "lag_365d_revenue"])

    def test_growth_ratios_nan_when_no_history(self) -> None:
        df = self._make_history(400)
        idx = 0
        _update_row_features(df, idx)

        assert pd.isna(df.at[idx, "lag_1d_rev_wow_growth"])
        assert pd.isna(df.at[idx, "lag_1d_rev_mom_growth"])
        assert pd.isna(df.at[idx, "lag_1d_rev_yoy_growth"])

    def test_growth_ratios_computed(self) -> None:
        df = self._make_history(400)
        idx = 366
        _update_row_features(df, idx)

        lag1 = df.at[idx, "lag_1d_revenue"]
        lag8 = df.at[idx, "lag_8d_revenue"]
        expected_wow = lag1 / lag8 - 1
        assert df.at[idx, "lag_1d_rev_wow_growth"] == pytest.approx(expected_wow)

    def test_rolling_stats_computed(self) -> None:
        df = self._make_history(400)
        idx = 30
        _update_row_features(df, idx)

        win7 = df["revenue"].iloc[idx - 7 : idx].to_numpy()
        assert df.at[idx, "roll_mean_7d_revenue"] == pytest.approx(float(np.mean(win7)))
        assert df.at[idx, "roll_median_7d_revenue"] == pytest.approx(float(np.median(win7)))
        assert df.at[idx, "roll_std_7d_revenue"] == pytest.approx(
            float(np.std(win7, ddof=1)), abs=1e-6
        )

    def test_rolling_stats_nan_at_start(self) -> None:
        df = self._make_history(400)
        idx = 0
        _update_row_features(df, idx)

        assert pd.isna(df.at[idx, "roll_mean_7d_revenue"])
        assert pd.isna(df.at[idx, "roll_std_7d_revenue"])

    def test_baseline_updated(self) -> None:
        df = self._make_history(400)
        idx = 366
        _update_row_features(df, idx)

        assert df.at[idx, "revenue_baseline"] == df.at[idx, "lag_365d_revenue"]
        assert df.at[idx, "cogs_baseline"] == df.at[idx, "lag_365d_cogs"]

    def test_cogs_ratio_updated(self) -> None:
        df = self._make_history(400)
        idx = 10
        _update_row_features(df, idx)

        expected = df.at[idx, "cogs"] / df.at[idx, "revenue"]
        assert df.at[idx, "cogs_ratio"] == pytest.approx(expected)

    def test_acceleration_computed(self) -> None:
        df = self._make_history(400)
        # Compute two consecutive rows
        _update_row_features(df, 10)
        _update_row_features(df, 11)

        wow_diff = df.at[11, "lag_1d_rev_wow_growth"] - df.at[10, "lag_1d_rev_wow_growth"]
        assert df.at[11, "rev_wow_acceleration"] == pytest.approx(wow_diff)

    def test_lagged_residuals_populated(self) -> None:
        df = self._make_history(400)
        # Simulate previous recursive steps having updated residuals
        df.at[363, "revenue_residual"] = 100.0
        df.at[364, "revenue_residual"] = 110.0
        df.at[365, "revenue_residual"] = 123.0
        df.at[363, "cogs_residual"] = 40.0
        df.at[364, "cogs_residual"] = 42.0
        df.at[365, "cogs_residual"] = 45.0
        idx = 366
        _update_row_features(df, idx)

        assert df.at[idx, "lag_1d_rev_residual"] == 123.0
        assert df.at[idx, "lag_2d_rev_residual"] == 110.0
        assert df.at[idx, "lag_3d_rev_residual"] == 100.0
        assert df.at[idx, "lag_1d_cogs_residual"] == 45.0
        assert df.at[idx, "lag_2d_cogs_residual"] == 42.0
        assert df.at[idx, "lag_3d_cogs_residual"] == 40.0

    def test_lagged_residuals_before_window_are_nan(self) -> None:
        df = self._make_history(400)
        idx = 0
        _update_row_features(df, idx)

        assert pd.isna(df.at[idx, "lag_1d_rev_residual"])
        assert pd.isna(df.at[idx, "lag_2d_rev_residual"])
        assert pd.isna(df.at[idx, "lag_3d_rev_residual"])
        assert pd.isna(df.at[idx, "lag_1d_cogs_residual"])
        assert pd.isna(df.at[idx, "lag_2d_cogs_residual"])
        assert pd.isna(df.at[idx, "lag_3d_cogs_residual"])


class TestPrepareFutureFrame:
    def _make_history(self, n: int = 10) -> pd.DataFrame:
        dates = pd.date_range("2023-01-01", periods=n)
        df = pd.DataFrame({"sales_date": dates})
        for c in CALENDAR_FEATURES:
            df[c] = 0.0
        for c in _TARGET_DERIVED:
            df[c] = 0.0
        df["revenue"] = 1.0
        df["cogs"] = 0.8
        df["sessions"] = 100.0
        return df

    def test_future_has_all_calendar_features(self) -> None:
        history = self._make_history(10)
        scaffold = pd.DataFrame({"date": pd.date_range("2023-01-11", periods=3)})
        future = _prepare_future_frame(history, scaffold)

        for c in CALENDAR_FEATURES:
            assert c in future.columns, f"Missing calendar feature: {c}"

    def test_future_exogenous_forward_filled(self) -> None:
        history = self._make_history(10)
        history["sessions"] = 999.0
        scaffold = pd.DataFrame({"date": pd.date_range("2023-01-11", periods=3)})
        future = _prepare_future_frame(history, scaffold)

        assert (future["sessions"] == 999.0).all()

    def test_future_leap_year_handling(self) -> None:
        history = self._make_history(10)
        history["sales_date"] = pd.date_range("2020-02-27", periods=10)  # leap year
        scaffold = pd.DataFrame({"date": [pd.Timestamp("2020-02-29")]})
        future = _prepare_future_frame(history, scaffold)

        assert future["day_of_year"].iloc[0] == 60
        # day_of_year_cos uses 366 for leap year
        expected_cos = np.cos(2 * np.pi * 60 / 366)
        assert future["day_of_year_cos"].iloc[0] == pytest.approx(expected_cos)

    def test_future_tet_features(self) -> None:
        history = self._make_history(10)
        history["sales_date"] = pd.date_range("2023-01-01", periods=10)
        scaffold = pd.DataFrame({"date": [pd.Timestamp("2023-01-15")]})
        future = _prepare_future_frame(history, scaffold)

        assert future["is_pre_tet_rush"].iloc[0] == 1  # within 21 days of Tet 2023-01-22
        assert future["days_to_tet"].iloc[0] == 7

    def test_future_revenue_cogs_are_nan(self) -> None:
        history = self._make_history(10)
        scaffold = pd.DataFrame({"date": pd.date_range("2023-01-11", periods=3)})
        future = _prepare_future_frame(history, scaffold)

        assert future["revenue"].isna().all()
        assert future["cogs"].isna().all()
