"""Data-quality checks for the modeling mart.

All functions accept a ``warehouse`` path and return plain data structures
(dicts / DataFrames) so they can be consumed by reports, notebooks, or tests.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from datathon.utils.data_loaders import load_modeling_data
from datathon.utils.duckdb_io import connect


def check_mart_schema(warehouse: Path | None = None) -> dict:
    """Return column names, dtypes and row count for the feature mart."""
    df = load_modeling_data(warehouse)
    return {
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": list(df.columns),
        "dtypes": {c: str(df[c].dtype) for c in df.columns},
        "date_range": (df["sales_date"].min(), df["sales_date"].max()),
    }


def check_nulls(warehouse: Path | None = None) -> pd.Series:
    """Return the ratio of nulls per column, sorted descending."""
    df = load_modeling_data(warehouse)
    return df.isna().mean().sort_values(ascending=False)


def check_date_gaps(warehouse: Path | None = None) -> pd.DataFrame | None:
    """Return rows where the gap between consecutive dates is not 1 day."""
    df = load_modeling_data(warehouse)
    gaps = df["sales_date"].diff().dt.days
    mask = gaps.notna() & (gaps != 1)
    bad = df[mask].copy()
    if bad.empty:
        return None
    bad["gap_days"] = gaps[mask]
    return bad[["sales_date", "gap_days"]]


def check_row_counts(warehouse: Path | None = None) -> dict:
    """Compare row counts across related marts to detect drift."""
    from datathon.utils.paths import warehouse_path

    wh = warehouse or warehouse_path()
    results: dict[str, int] = {}
    with connect(wh) as conn:
        for mart in [
            "marts.mart_forecast_daily_base",
            "marts.mart_forecast_daily_features",
            "marts.mart_submission_scaffold",
        ]:
            try:
                cnt = conn.execute(f"select count(*) from {mart}").fetchone()[0]
                results[mart] = int(cnt)
            except Exception:
                results[mart] = -1
    return results
