"""Daily promo intensity features from historical promotion schedule."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from datathon.utils.duckdb_io import connect
from datathon.utils.paths import warehouse_path


def _load_promotions(warehouse: Path | None = None) -> pd.DataFrame:
    """Load stg_promotions from DuckDB warehouse."""
    wh = warehouse or warehouse_path()
    query = """
        select
            promo_name,
            start_date,
            end_date,
            promo_type,
            discount_value,
            promo_channel,
            stackable_flag,
            applicable_category,
            min_order_value
        from staging.stg_promotions
    """
    with connect(wh) as conn:
        df = conn.execute(query).fetchdf()
    df["start_date"] = pd.to_datetime(df["start_date"])
    df["end_date"] = pd.to_datetime(df["end_date"])
    return df


def _build_historical_daily(promo_df: pd.DataFrame, date_range: pd.DatetimeIndex) -> pd.DataFrame:
    """Explode promotion periods into daily rows and aggregate."""
    if promo_df.empty:
        return pd.DataFrame(
            {
                "sales_date": date_range,
                "promo_count": 0.0,
                "promo_max_discount": 0.0,
                "promo_mean_discount": 0.0,
                "promo_max_min_order_value": 0.0,
                "promo_stackable_count": 0.0,
                "is_promo": 0.0,
            }
        )

    rows = []
    for _, row in promo_df.iterrows():
        dates = pd.date_range(row["start_date"], row["end_date"], freq="D")
        for d in dates:
            rows.append(
                {
                    "sales_date": d,
                    "discount_value": row["discount_value"],
                    "min_order_value": row["min_order_value"],
                    "stackable_flag": float(row["stackable_flag"]),
                }
            )

    daily = pd.DataFrame(rows)
    if daily.empty:
        return pd.DataFrame(
            {
                "sales_date": date_range,
                "promo_count": 0.0,
                "promo_max_discount": 0.0,
                "promo_mean_discount": 0.0,
                "promo_max_min_order_value": 0.0,
                "promo_stackable_count": 0.0,
                "is_promo": 0.0,
            }
        )

    agg = (
        daily.groupby("sales_date")
        .agg(
            promo_count=("sales_date", "size"),
            promo_max_discount=("discount_value", "max"),
            promo_mean_discount=("discount_value", "mean"),
            promo_max_min_order_value=("min_order_value", "max"),
            promo_stackable_count=("stackable_flag", "sum"),
        )
        .reset_index()
    )
    agg["is_promo"] = 1.0

    full = pd.DataFrame({"sales_date": date_range})
    full = full.merge(agg, on="sales_date", how="left")
    fill_cols = [
        "promo_count",
        "promo_max_discount",
        "promo_mean_discount",
        "promo_max_min_order_value",
        "promo_stackable_count",
        "is_promo",
    ]
    full[fill_cols] = full[fill_cols].fillna(0.0)
    return full


def _detect_pattern(years: list[int]) -> str:
    """Detect odd/even/all year pattern for a promotion event."""
    if all(y % 2 == 1 for y in years):
        return "odd"
    if all(y % 2 == 0 for y in years):
        return "even"
    return "all"


def _build_future_promo(
    promo_df: pd.DataFrame,
    start_year: int,
    end_year: int,
) -> pd.DataFrame:
    """Predict future daily promo schedule from historical patterns."""
    if promo_df.empty:
        date_range = pd.date_range(f"{start_year}-01-01", f"{end_year}-12-31", freq="D")
        return pd.DataFrame(
            {
                "sales_date": date_range,
                "promo_count": 0.0,
                "promo_max_discount": 0.0,
                "promo_mean_discount": 0.0,
                "promo_max_min_order_value": 0.0,
                "promo_stackable_count": 0.0,
                "is_promo": 0.0,
            }
        )

    # Extract event name (remove trailing year)
    promo_df = promo_df.copy()
    promo_df["event_name"] = (
        promo_df["promo_name"].str.replace(r"\s+\d{4}$", "", regex=True).str.strip()
    )
    promo_df["start_year"] = promo_df["start_date"].dt.year
    promo_df["start_month"] = promo_df["start_date"].dt.month
    promo_df["start_day"] = promo_df["start_date"].dt.day
    promo_df["duration_days"] = (promo_df["end_date"] - promo_df["start_date"]).dt.days

    # Build rules per event
    rules = (
        promo_df.groupby("event_name")
        .agg(
            start_month=("start_month", lambda x: int(x.median())),
            start_day=("start_day", lambda x: int(x.median())),
            duration_days=("duration_days", lambda x: int(x.median())),
            promo_type=("promo_type", "first"),
            discount_value=("discount_value", "median"),
            promo_channel=("promo_channel", "first"),
            stackable_flag=("stackable_flag", "first"),
            applicable_category=("applicable_category", "first"),
            min_order_value=("min_order_value", "first"),
        )
        .reset_index()
    )

    # Detect year pattern
    year_patterns = (
        promo_df.groupby("event_name")["start_year"]
        .apply(lambda x: sorted(x.unique().tolist()))
        .reset_index(name="years")
    )
    year_patterns["pattern"] = year_patterns["years"].apply(_detect_pattern)
    rules = rules.merge(year_patterns[["event_name", "pattern"]], on="event_name", how="left")

    # Generate future promo dates
    all_promos = []
    for year in range(start_year, end_year + 1):
        for _, row in rules.iterrows():
            if row["pattern"] == "odd" and year % 2 == 0:
                continue
            if row["pattern"] == "even" and year % 2 == 1:
                continue

            start = pd.Timestamp(
                year=year, month=int(row["start_month"]), day=int(row["start_day"])
            )
            end = start + pd.Timedelta(days=int(row["duration_days"]))
            dates = pd.date_range(start, end, freq="D")

            for d in dates:
                all_promos.append(
                    {
                        "sales_date": d,
                        "discount_value": row["discount_value"],
                        "min_order_value": row["min_order_value"],
                        "stackable_flag": float(row["stackable_flag"]),
                    }
                )

    if not all_promos:
        date_range = pd.date_range(f"{start_year}-01-01", f"{end_year}-12-31", freq="D")
        return pd.DataFrame(
            {
                "sales_date": date_range,
                "promo_count": 0.0,
                "promo_max_discount": 0.0,
                "promo_mean_discount": 0.0,
                "promo_max_min_order_value": 0.0,
                "promo_stackable_count": 0.0,
                "is_promo": 0.0,
            }
        )

    daily = pd.DataFrame(all_promos)
    agg = (
        daily.groupby("sales_date")
        .agg(
            promo_count=("sales_date", "size"),
            promo_max_discount=("discount_value", "max"),
            promo_mean_discount=("discount_value", "mean"),
            promo_max_min_order_value=("min_order_value", "max"),
            promo_stackable_count=("stackable_flag", "sum"),
        )
        .reset_index()
    )
    agg["is_promo"] = 1.0

    date_range = pd.date_range(f"{start_year}-01-01", f"{end_year}-12-31", freq="D")
    full = pd.DataFrame({"sales_date": date_range})
    full = full.merge(agg, on="sales_date", how="left")
    fill_cols = [
        "promo_count",
        "promo_max_discount",
        "promo_mean_discount",
        "promo_max_min_order_value",
        "promo_stackable_count",
        "is_promo",
    ]
    full[fill_cols] = full[fill_cols].fillna(0.0)
    return full


def build_promo_features(
    df: pd.DataFrame,
    warehouse: Path | None = None,
) -> pd.DataFrame:
    """Merge daily promo intensity features into the modeling DataFrame.

    Historical dates (<= max(sales_date)) use actual promotions.
    Future dates use pattern-based prediction from historical promo schedule.
    """
    promo_df = _load_promotions(warehouse)
    if promo_df.empty:
        for col in [
            "promo_count",
            "promo_max_discount",
            "promo_mean_discount",
            "promo_max_min_order_value",
            "promo_stackable_count",
            "is_promo",
        ]:
            df[col] = 0.0
        return df

    df = df.copy()
    df["sales_date"] = pd.to_datetime(df["sales_date"])

    min_date = df["sales_date"].min()
    max_date = df["sales_date"].max()

    # Historical
    hist_daily = _build_historical_daily(promo_df, pd.date_range(min_date, max_date, freq="D"))

    # Future (only if needed — e.g. for forecast scaffold)
    future_dates = df[df["sales_date"] > max_date]["sales_date"].unique()
    if len(future_dates) > 0:
        future_start = int(future_dates.min().year)
        future_end = int(future_dates.max().year)
        future_daily = _build_future_promo(promo_df, future_start, future_end)
        hist_daily = pd.concat([hist_daily, future_daily], ignore_index=True)
        hist_daily = hist_daily.drop_duplicates(subset=["sales_date"], keep="last")

    df = df.merge(hist_daily, on="sales_date", how="left")
    fill_cols = [
        "promo_count",
        "promo_max_discount",
        "promo_mean_discount",
        "promo_max_min_order_value",
        "promo_stackable_count",
        "is_promo",
    ]
    df[fill_cols] = df[fill_cols].fillna(0.0)
    return df
