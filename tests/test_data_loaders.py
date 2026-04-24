from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from datathon.utils.data_loaders import load_forecast_base, load_modeling_data, load_scaffold


def _make_mock_conn(df: pd.DataFrame) -> MagicMock:
    conn = MagicMock()
    conn.execute.return_value.fetchdf.return_value = df
    return conn


class TestLoadModelingData:
    @patch("datathon.utils.data_loaders.connect")
    def test_loads_and_parses_dates(self, mock_connect) -> None:
        df = pd.DataFrame(
            {
                "sales_date": ["2023-01-01", "2023-01-02"],
                "revenue": [100.0, 200.0],
                "feature_a": [1, 2],
            }
        )
        mock_connect.return_value.__enter__.return_value = _make_mock_conn(df)

        result = load_modeling_data(warehouse="dummy.duckdb")
        assert pd.api.types.is_datetime64_any_dtype(result["sales_date"])
        assert len(result) == 2
        assert "revenue" in result.columns

    @patch("datathon.utils.data_loaders.connect")
    def test_raises_on_empty_result(self, mock_connect) -> None:
        mock_connect.return_value.__enter__.return_value = _make_mock_conn(
            pd.DataFrame(columns=["sales_date", "revenue"])
        )

        with pytest.raises(RuntimeError, match="no rows"):
            load_modeling_data(warehouse="dummy.duckdb")

    @patch("datathon.utils.data_loaders.connect")
    def test_casts_int_columns_to_float(self, mock_connect) -> None:
        df = pd.DataFrame(
            {
                "sales_date": ["2023-01-01"],
                "revenue": pd.array([100], dtype="Int64"),
                "flag": pd.array([1], dtype="Int32"),
            }
        )
        mock_connect.return_value.__enter__.return_value = _make_mock_conn(df)

        result = load_modeling_data(warehouse="dummy.duckdb")
        assert result["revenue"].dtype == float
        assert result["flag"].dtype == float


class TestLoadForecastBase:
    @patch("datathon.utils.data_loaders.connect")
    def test_loads_revenue_cogs_only(self, mock_connect) -> None:
        df = pd.DataFrame(
            {
                "sales_date": ["2023-01-01", "2023-01-02"],
                "revenue": [100.0, 200.0],
                "cogs": [80.0, 160.0],
            }
        )
        mock_connect.return_value.__enter__.return_value = _make_mock_conn(df)

        result = load_forecast_base(warehouse="dummy.duckdb")
        assert list(result.columns) == ["sales_date", "revenue", "cogs"]
        assert pd.api.types.is_datetime64_any_dtype(result["sales_date"])


class TestLoadScaffold:
    @patch("datathon.utils.data_loaders.connect")
    def test_loads_date_column(self, mock_connect) -> None:
        df = pd.DataFrame({"date": ["2023-01-01", "2023-01-02"]})
        mock_connect.return_value.__enter__.return_value = _make_mock_conn(df)

        result = load_scaffold(warehouse="dummy.duckdb")
        assert list(result.columns) == ["date"]
        assert pd.api.types.is_datetime64_any_dtype(result["date"])
        assert len(result) == 2
