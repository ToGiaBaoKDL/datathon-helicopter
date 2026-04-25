"""Feature selection analysis — investigates importance, correlation, and redundancy
across all registered models to recommend a leaner feature set.

Usage::

    uv run python -m audit.feature_selection
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from datathon.modeling.forecasters.catboost import CatBoostForecaster
from datathon.modeling.forecasters.lightgbm import LightGBMForecaster
from datathon.modeling.forecasters.xgboost import XGBoostForecaster
from datathon.modeling.recursive import feature_columns
from datathon.utils.paths import warehouse_path


def compute_model_importances(df: pd.DataFrame, feature_cols: list[str]) -> pd.DataFrame:
    """Train quick models and collect feature importances."""
    train_df = df.dropna(subset=["revenue_residual", "cogs_residual"])
    X = train_df[feature_cols].fillna(0)
    y_rev = train_df["revenue_residual"]
    y_cogs = train_df["cogs_residual"]

    models = {
        "lightgbm": LightGBMForecaster(n_estimators=200, learning_rate=0.05, verbose=-1),
        "xgboost": XGBoostForecaster(n_estimators=200, learning_rate=0.05, verbosity=0),
        "catboost": CatBoostForecaster(iterations=200, learning_rate=0.05, verbose=False),
    }

    records = []
    for model_name, forecaster in models.items():
        print(f"Training {model_name} ...")
        forecaster.fit(X, y_rev, y_cogs)

        for target in ["rev", "cogs"]:
            model = getattr(forecaster, f"model_{target}")
            if hasattr(model, "feature_importances_"):
                imp = model.feature_importances_
            elif hasattr(model, "get_booster"):
                score = model.get_booster().get_score(importance_type="gain")
                imp = [score.get(f"f{i}", 0) for i in range(len(feature_cols))]
            elif hasattr(model, "get_feature_importance"):
                imp = model.get_feature_importance()
            else:
                continue

            for feat, val in zip(feature_cols, imp, strict=True):
                records.append(
                    {
                        "model": model_name,
                        "target": target,
                        "feature": feat,
                        "importance": float(val),
                    }
                )

    return pd.DataFrame(records)


def analyze_correlations(df: pd.DataFrame, feature_cols: list[str]) -> pd.DataFrame:
    """Find highly correlated feature pairs (redundancy)."""
    corr_matrix = df[feature_cols].corr().abs()
    pairs = []
    for i in range(len(feature_cols)):
        for j in range(i + 1, len(feature_cols)):
            pairs.append(
                {
                    "feat_a": feature_cols[i],
                    "feat_b": feature_cols[j],
                    "corr": corr_matrix.iloc[i, j],
                }
            )
    pairs_df = pd.DataFrame(pairs).sort_values("corr", ascending=False)
    return pairs_df[pairs_df["corr"] > 0.95]


def main() -> None:
    # Use read-only connection to avoid conflicting with running dbt/CLI processes
    wh = warehouse_path()
    conn = duckdb.connect(str(wh), read_only=True)
    df = conn.execute(
        "select * from marts.mart_forecast_daily_features order by sales_date"
    ).fetchdf()
    conn.close()
    df["sales_date"] = pd.to_datetime(df["sales_date"])
    for col in df.columns:
        if df[col].dtype.name in ("Int64", "Int32", "Float64", "boolean", "BooleanDtype"):
            df[col] = df[col].astype(float)

    feat_cols = feature_columns(df)
    print(f"Features: {len(feat_cols)}")

    # 1. Model importances
    print("\n=== Computing model importances ===")
    imp_df = compute_model_importances(df, feat_cols)

    # Aggregate: mean importance across models & targets, normalized per model
    imp_df["norm_importance"] = imp_df.groupby(["model", "target"])["importance"].transform(
        lambda x: x / x.max()
    )
    agg = (
        imp_df.groupby("feature")
        .agg(mean_norm=("norm_importance", "mean"), mean_raw=("importance", "mean"))
        .sort_values("mean_norm", ascending=False)
    )

    print("\n=== Top 20 features (mean normalized importance across 3 models) ===")
    for feat, row in agg.head(20).iterrows():
        print(f"  {feat:<35} {row['mean_norm']:.4f}")

    print("\n=== Bottom 20 features (potential drop candidates) ===")
    for feat, row in agg.tail(20).iterrows():
        print(f"  {feat:<35} {row['mean_norm']:.4f}")

    # 2. Redundancy check
    print("\n=== Highly correlated pairs (|corr| > 0.95) ===")
    redundant = analyze_correlations(df, feat_cols)
    if redundant.empty:
        print("  None found.")
    else:
        print(redundant.to_string(index=False))

    # 3. Recommendations
    weak_threshold = 0.01
    weak_features = agg[agg["mean_norm"] < weak_threshold].index.tolist()

    print("\n=== Recommendations ===")
    print(f"Weak features (mean_norm < {weak_threshold}): {len(weak_features)}")
    for f in weak_features:
        print(f"  - {f}: {agg.loc[f, 'mean_norm']:.4f}")

    # Save report
    out = Path("reports/feature_importance.csv")
    out.parent.mkdir(exist_ok=True)
    agg.to_csv(out)
    print(f"\nFull report: {out}")


if __name__ == "__main__":
    main()
