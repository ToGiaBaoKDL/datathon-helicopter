"""Centralised data-loading helpers for DuckDB marts."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from datathon.utils.duckdb_io import connect
from datathon.utils.paths import models_dir, warehouse_path


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


def _ensure_derived_targets(df: pd.DataFrame, target_transform: str) -> pd.DataFrame:
    """Compute derived target columns (log, residual) if missing."""
    if target_transform == "log":
        if "log_revenue" not in df.columns:
            df["log_revenue"] = np.log1p(df["revenue"])
        if "log_cogs" not in df.columns:
            df["log_cogs"] = np.log1p(df["cogs"])
    return df


def _fit_prophet_baseline(
    df: pd.DataFrame, warehouse: Path | None = None, log_transform: bool = False
) -> object:
    """Fit or load cached Prophet baseline models.

    The cache is invalidated when the DuckDB warehouse file is newer than
    the cache, ensuring Prophet is refit after dbt rebuilds.
    """
    from datathon.modeling.prophet_baseline import ProphetBaseline

    cache_path = models_dir() / "prophet_baseline.pkl"
    wh = warehouse or warehouse_path()

    if cache_path.exists() and wh.exists():
        cache_mtime = cache_path.stat().st_mtime
        wh_mtime = wh.stat().st_mtime
        if cache_mtime >= wh_mtime:
            pb = ProphetBaseline.load(cache_path)
            # Invalidate cache if log_transform mismatch
            if getattr(pb, "_log_transform", False) == log_transform:
                return pb

    pb = ProphetBaseline()
    pb.fit(df, log_transform=log_transform)
    pb.save(cache_path)
    return pb


def _apply_prophet_baseline(
    df: pd.DataFrame, warehouse: Path | None = None, log_transform: bool = False
) -> pd.DataFrame:
    """Overwrite additive decomposition baselines with Prophet predictions."""
    pb = _fit_prophet_baseline(df, warehouse, log_transform=log_transform)
    baseline_df = pb.predict_history(df)

    df = df.merge(baseline_df, on="sales_date", how="left")
    # Overwrite additive decomposition baselines
    if log_transform:
        # Prophet baselines are in log-space; keep both log and raw variants
        df["log_revenue_baseline"] = df["prophet_revenue_baseline"]
        df["log_cogs_baseline"] = df["prophet_cogs_baseline"]
        df["revenue_baseline"] = np.expm1(df["prophet_revenue_baseline"])
        df["cogs_baseline"] = np.expm1(df["prophet_cogs_baseline"])
        # Recompute residuals in log space
        df["revenue_residual"] = np.log1p(df["revenue"]) - df["log_revenue_baseline"]
        df["cogs_residual"] = np.log1p(df["cogs"]) - df["log_cogs_baseline"]
    else:
        df["revenue_baseline"] = df["prophet_revenue_baseline"]
        df["cogs_baseline"] = df["prophet_cogs_baseline"]
        if "log_revenue_baseline" in df.columns:
            df["log_revenue_baseline"] = np.log1p(df["prophet_revenue_baseline"].clip(lower=0))
        if "log_cogs_baseline" in df.columns:
            df["log_cogs_baseline"] = np.log1p(df["prophet_cogs_baseline"].clip(lower=0))
        # Recompute residuals in raw space
        df["revenue_residual"] = df["revenue"] - df["revenue_baseline"]
        df["cogs_residual"] = df["cogs"] - df["cogs_baseline"]
    return df


def _apply_promo_features(df: pd.DataFrame, warehouse: Path | None = None) -> pd.DataFrame:
    """Merge daily promo intensity features into the modeling DataFrame."""
    from datathon.features.promo_features import build_promo_features

    return build_promo_features(df, warehouse=warehouse)


def _apply_promo_features_to_scaffold(
    scaffold: pd.DataFrame, warehouse: Path | None = None
) -> pd.DataFrame:
    """Merge daily promo intensity features into the forecast scaffold.

    Future promo schedule is predicted from historical patterns (odd/even
    year detection + median timing/duration) so the model sees the same
    promo signal at inference time that it saw during training.
    """
    from datathon.features.promo_features import _build_future_promo, _load_promotions

    promo_df = _load_promotions(warehouse)
    fill_cols = [
        "promo_count",
        "promo_max_discount",
        "promo_mean_discount",
        "promo_max_min_order_value",
        "promo_stackable_count",
        "is_promo",
    ]

    if promo_df.empty:
        for col in fill_cols:
            scaffold[col] = 0.0
        return scaffold

    scaffold = scaffold.copy()
    scaffold["date"] = pd.to_datetime(scaffold["date"])

    future_start = int(scaffold["date"].min().year)
    future_end = int(scaffold["date"].max().year)
    future_daily = _build_future_promo(promo_df, future_start, future_end)

    scaffold = scaffold.merge(
        future_daily.rename(columns={"sales_date": "date"}),
        on="date",
        how="left",
    )
    for col in fill_cols:
        if col not in scaffold.columns:
            scaffold[col] = 0.0
    scaffold[fill_cols] = scaffold[fill_cols].fillna(0.0)
    return scaffold


def load_training_data(
    config: dict | None = None,
    warehouse: Path | None = None,
) -> pd.DataFrame:
    """Load modeling data and optionally filter by ``train_start_date``."""
    df = load_modeling_data(warehouse)

    if config is not None:
        target_transform = config.get("target_transform", "identity")
        df = _ensure_derived_targets(df, target_transform)

        if config.get("prophet_baseline", False):
            log_transform = config.get("target_transform") == "log_residual"
            df = _apply_prophet_baseline(df, warehouse, log_transform=log_transform)

        if config.get("promo_features", False):
            df = _apply_promo_features(df, warehouse)

        start_date = config.get("train_start_date")
        if start_date is not None:
            try:
                start_ts = pd.to_datetime(start_date)
            except Exception as exc:
                raise ValueError(f"Invalid train_start_date={start_date!r}: {exc}") from exc

            min_date = df["sales_date"].min()
            max_date = df["sales_date"].max()

            if start_ts < min_date:
                raise ValueError(
                    f"train_start_date={start_ts.date()} is before the earliest "
                    f"data ({min_date.date()})."
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
