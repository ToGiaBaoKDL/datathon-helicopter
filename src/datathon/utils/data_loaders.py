"""Centralised data-loading helpers for DuckDB marts."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from datathon.utils.duckdb_io import connect
from datathon.utils.paths import warehouse_path


def load_modeling_data(warehouse: Path | None = None) -> pd.DataFrame:
    """Load ``marts.mart_forecast_daily_modeling`` ordered by date."""
    wh = warehouse or warehouse_path()
    query = """
        select *
        from marts.mart_forecast_daily_modeling
        order by sales_date
    """
    with connect(wh) as conn:
        df = conn.execute(query).fetchdf()

    for col in df.columns:
        if col == "sales_date":
            continue
        if df[col].dtype.name in ("Int64", "Int32", "Float64", "boolean", "BooleanDtype"):
            df[col] = df[col].astype(float)
    return df


def load_forecast_base(warehouse: Path | None = None) -> pd.DataFrame:
    """Load ``marts.mart_forecast_daily_base`` (sales_date, revenue, cogs)."""
    wh = warehouse or warehouse_path()
    query = """
        select sales_date, revenue, cogs
        from marts.mart_forecast_daily_base
        order by sales_date
    """
    with connect(wh) as conn:
        return conn.execute(query).fetchdf()


def load_scaffold(warehouse: Path | None = None) -> pd.DataFrame:
    """Load ``marts.mart_submission_scaffold`` ordered by date."""
    wh = warehouse or warehouse_path()
    query = """
        select date, revenue, cogs
        from marts.mart_submission_scaffold
        order by date
    """
    with connect(wh) as conn:
        return conn.execute(query).fetchdf()
