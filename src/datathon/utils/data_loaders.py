"""Centralised data-loading helpers for DuckDB marts."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from datathon.utils.duckdb_io import connect
from datathon.utils.paths import warehouse_path


def load_modeling_data(warehouse: Path | None = None) -> pd.DataFrame:
    """Load ``marts.mart_forecast_daily_features`` ordered by date."""
    wh = warehouse or warehouse_path()
    query = """
        select *
        from marts.mart_forecast_daily_features
        order by sales_date
    """
    with connect(wh) as conn:
        df = conn.execute(query).fetchdf()

    df["sales_date"] = pd.to_datetime(df["sales_date"])

    for col in df.columns:
        if col == "sales_date":
            continue
        if df[col].dtype.name in ("Int64", "Int32", "Float64", "boolean", "BooleanDtype"):
            df[col] = df[col].astype(float)

    if df.empty:
        raise RuntimeError("mart_forecast_daily_features returned no rows.")

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
        df = conn.execute(query).fetchdf()
    df["sales_date"] = pd.to_datetime(df["sales_date"])
    return df


def load_training_data(
    config: dict | None = None,
    warehouse: Path | None = None,
) -> pd.DataFrame:
    """Load modeling data and optionally filter by ``train_start_date``."""
    df = load_modeling_data(warehouse)

    if config is None:
        return df

    start_date = config.get("train_start_date")
    if start_date is None:
        return df

    try:
        start_ts = pd.to_datetime(start_date)
    except Exception as exc:
        raise ValueError(f"Invalid train_start_date={start_date!r}: {exc}") from exc

    min_date = df["sales_date"].min()
    max_date = df["sales_date"].max()

    if start_ts < min_date:
        raise ValueError(
            f"train_start_date={start_ts.date()} is before the earliest data ({min_date.date()})."
        )
    if start_ts > max_date:
        raise ValueError(
            f"train_start_date={start_ts.date()} is after the latest "
            f"data ({max_date.date()}). After filtering, no rows remain."
        )

    df = df[df["sales_date"] >= start_ts].copy().reset_index(drop=True)

    if len(df) < 1_000:
        raise ValueError(
            f"train_start_date={start_ts.date()} leaves only {len(df)} rows. "
            f"Need at least 1,000 rows for reliable training."
        )

    return df


def load_scaffold(warehouse: Path | None = None) -> pd.DataFrame:
    """Load ``marts.mart_submission_scaffold`` ordered by date."""

    wh = warehouse or warehouse_path()
    query = """
        select date
        from marts.mart_submission_scaffold
        order by date
    """
    with connect(wh) as conn:
        df = conn.execute(query).fetchdf()
    df["date"] = pd.to_datetime(df["date"])
    return df
