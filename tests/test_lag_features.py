from __future__ import annotations

import pandas as pd

from datathon.features.lag_features import add_revenue_lag_features, add_revenue_rolling_features


def test_add_revenue_lag_features_creates_expected_columns() -> None:
    frame = pd.DataFrame(
        {
            "sales_date": pd.date_range("2023-01-01", periods=5, freq="D"),
            "revenue": [10, 20, 30, 40, 50],
        }
    )

    output = add_revenue_lag_features(frame, lags=[1, 2])

    assert "lag_1d_revenue" in output.columns
    assert "lag_2d_revenue" in output.columns
    assert pd.isna(output.loc[0, "lag_1d_revenue"])
    assert output.loc[2, "lag_1d_revenue"] == 20


def test_add_revenue_rolling_features_creates_expected_columns() -> None:
    frame = pd.DataFrame(
        {
            "sales_date": pd.date_range("2023-01-01", periods=10, freq="D"),
            "revenue": list(range(10, 110, 10)),
        }
    )

    output = add_revenue_rolling_features(frame, windows=[3])

    assert "roll_mean_3d_revenue" in output.columns
    assert "roll_std_3d_revenue" in output.columns
