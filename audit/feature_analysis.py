"""Feature-analysis helpers for the modeling mart.

Provides correlation audits, quick feature-importance sketches, and
autocorrelation summaries without hard-coding paths.
"""

from __future__ import annotations

from pathlib import Path

import lightgbm as lgb
import pandas as pd

from datathon.modeling.recursive import feature_columns
from datathon.utils.data_loaders import load_modeling_data


def target_stats(warehouse: Path | None = None) -> dict:
    """Basic stats for raw and residual targets."""
    df = load_modeling_data(warehouse)
    return {
        "revenue": {"mean": float(df["revenue"].mean()), "std": float(df["revenue"].std())},
        "cogs": {"mean": float(df["cogs"].mean()), "std": float(df["cogs"].std())},
        "revenue_residual": {
            "mean": float(df["revenue_residual"].mean()),
            "std": float(df["revenue_residual"].std()),
        },
        "cogs_residual": {
            "mean": float(df["cogs_residual"].mean()),
            "std": float(df["cogs_residual"].std()),
        },
        "residual_std_over_revenue_std": float(df["revenue_residual"].std() / df["revenue"].std()),
    }


def feature_correlations(warehouse: Path | None = None, top_n: int = 15) -> dict:
    """Top-N absolute correlations with revenue, cogs, and residual targets."""
    df = load_modeling_data(warehouse)
    cols = feature_columns(df)
    targets = {
        "revenue": df["revenue"],
        "cogs": df["cogs"],
        "revenue_residual": df["revenue_residual"],
        "cogs_residual": df["cogs_residual"],
    }
    out: dict[str, pd.Series] = {}
    for name, y in targets.items():
        corrs = df[cols].corrwith(y).abs().sort_values(ascending=False).head(top_n)
        out[name] = corrs
    return out


def quick_feature_importance(warehouse: Path | None = None, top_n: int = 20) -> dict:
    """Train a quick LightGBM and return mean-split feature importances."""
    df = load_modeling_data(warehouse)
    cols = feature_columns(df)
    train_df = df.dropna(subset=["revenue_residual", "cogs_residual"])
    X = train_df[cols].fillna(0)
    y_rev = train_df["revenue_residual"]
    y_cogs = train_df["cogs_residual"]

    out: dict[str, pd.Series] = {}
    for target, y in [("revenue_residual", y_rev), ("cogs_residual", y_cogs)]:
        model = lgb.LGBMRegressor(n_estimators=100, learning_rate=0.1, verbose=-1)
        model.fit(X, y)
        imp = pd.Series(model.feature_importances_, index=cols).sort_values(ascending=False)
        out[target] = imp.head(top_n)
    return out


def autocorrelations(warehouse: Path | None = None, lags: list[int] | None = None) -> dict:
    """Autocorrelation of revenue and revenue_residual at selected lags."""
    df = load_modeling_data(warehouse)
    lags = lags or [1, 7, 14, 28, 365]
    out: dict[str, dict[int, float]] = {}
    for col in ["revenue", "revenue_residual"]:
        out[col] = {lag: float(df[col].autocorr(lag=lag)) for lag in lags}
    return out
