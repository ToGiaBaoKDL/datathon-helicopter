"""Feature importance analysis combining split-based, permutation, and SHAP importance."""

from __future__ import annotations

from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
import shap
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split

from datathon.modeling.recursive import feature_columns
from datathon.utils.data_loaders import load_modeling_data


def _tier(threshold: float) -> str:
    if threshold >= 0.05:
        return "TIER 1 -- STRONG"
    if threshold >= 0.01:
        return "TIER 2 -- MEDIUM"
    return "TIER 3 -- WEAK"


def lgb_importance(
    df: pd.DataFrame,
    target_col: str = "revenue_residual",
    n_estimators: int = 300,
    top_n: int | None = None,
) -> pd.DataFrame:
    """Return split-based feature importance from a quick LightGBM fit."""
    cols = feature_columns(df)
    X = df[cols].fillna(0)
    y = df[target_col]

    model = lgb.LGBMRegressor(n_estimators=n_estimators, learning_rate=0.1, verbose=-1)
    model.fit(X, y)

    imp = pd.Series(model.feature_importances_, index=cols, name="lgb_gain")
    imp = imp.sort_values(ascending=False)
    if top_n:
        imp = imp.head(top_n)

    total = imp.sum()
    imp_pct = (imp / total * 100).round(2)
    result = imp.reset_index()
    result.columns = ["feature", "lgb_gain", "lgb_gain_pct"]
    result["lgb_gain_pct"] = imp_pct.values
    result["tier"] = result["lgb_gain_pct"].apply(lambda p: _tier(p / 100))
    return result


def permutation_importance(
    df: pd.DataFrame,
    target_col: str = "revenue_residual",
    val_frac: float = 0.2,
    n_estimators: int = 300,
    n_repeats: int = 5,
    random_state: int = 42,
    top_n: int | None = None,
) -> pd.DataFrame:
    """Compute permutation importance on a held-out validation slice."""
    rng = np.random.RandomState(random_state)
    cols = feature_columns(df)
    X = df[cols].fillna(0)
    y = df[target_col]

    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=val_frac, shuffle=False)

    model = lgb.LGBMRegressor(n_estimators=n_estimators, learning_rate=0.1, verbose=-1)
    model.fit(X_train, y_train)

    baseline_mae = float(mean_absolute_error(y_val, model.predict(X_val)))
    result_rows = []

    for col in cols:
        scores = []
        for _ in range(n_repeats):
            X_shuffled = X_val.copy().values
            rng.shuffle(X_shuffled[:, cols.index(col)])
            shuffled_df = pd.DataFrame(X_shuffled, columns=cols, index=X_val.index)
            mae_shuffled = mean_absolute_error(y_val, model.predict(shuffled_df))
            scores.append(mae_shuffled - baseline_mae)

        result_rows.append(
            {
                "feature": col,
                "perm_importance": np.mean(scores),
                "perm_std": np.std(scores),
            }
        )

    result = pd.DataFrame(result_rows)
    result = result.sort_values("perm_importance", ascending=False)
    if top_n:
        result = result.head(top_n)

    result["perm_importance_pct"] = (result["perm_importance"] / baseline_mae * 100).round(2)
    result["tier"] = result["perm_importance_pct"].apply(lambda p: _tier(p / 100))
    return result


def shap_importance(
    forecaster,
    background_df: pd.DataFrame,
    sample_size: int = 500,
    top_n: int | None = None,
) -> pd.DataFrame:
    """Compute mean |SHAP value| importance for each target."""
    cols = feature_columns(background_df)
    X_bg = background_df[cols].fillna(0)

    X_bg = X_bg.sample(n=sample_size, random_state=42) if len(X_bg) > sample_size else X_bg

    results = []
    for target, model in (("revenue", forecaster.model_rev), ("cogs", forecaster.model_cogs)):
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_bg)
        if isinstance(shap_values, list):
            shap_values = shap_values[0]

        mean_abs = pd.Series(shap_values.mean(axis=0), index=cols).abs()
        mean_abs.name = f"shap_{target}"
        results.append(mean_abs.reset_index())
        results[-1].columns = ["feature", f"shap_{target}"]

    merged = results[0].merge(results[1], on="feature")
    merged["shap_avg"] = (merged["shap_revenue"] + merged["shap_cogs"]) / 2
    merged = merged.sort_values("shap_avg", ascending=False)
    if top_n:
        merged = merged.head(top_n)

    total = merged["shap_avg"].sum()
    merged["shap_pct"] = (merged["shap_avg"] / total * 100).round(2)
    merged["tier"] = merged["shap_pct"].apply(lambda p: _tier(p / 100))
    return merged


def full_report(warehouse: Path | None = None) -> pd.DataFrame:
    """Run split-based and permutation importance methods and merge into one ranked table."""
    df = load_modeling_data(warehouse)

    lgb_df = lgb_importance(df)
    perm_df = permutation_importance(df)

    merged = lgb_df.merge(
        perm_df[["feature", "perm_importance", "perm_std", "perm_importance_pct"]],
        on="feature",
        how="outer",
    )
    merged = merged.sort_values("lgb_gain_pct", ascending=False).reset_index(drop=True)
    return merged
