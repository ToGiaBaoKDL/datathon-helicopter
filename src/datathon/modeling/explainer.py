"""SHAP explainability for forecasters."""

from __future__ import annotations

import warnings

import pandas as pd

from datathon.modeling.forecasters.base import BaseForecaster
from datathon.modeling.recursive import feature_columns


def explain_forecaster(
    forecaster: BaseForecaster,
    history: pd.DataFrame,
    sample_size: int | None = 500,
) -> dict[str, pd.DataFrame]:
    """Return SHAP values for revenue and COGS models.

    Parameters
    ----------
    forecaster:
        A fitted ``BaseForecaster``.
    history:
        Historical dataframe used for background distribution.
    sample_size:
        Number of rows to sample from *history* for the background dataset.
        ``None`` uses the full history (slower for large datasets).

    Returns
    -------
    Mapping of ``{"revenue": shap_df, "cogs": shap_df}`` where each
    DataFrame has columns ``[feature, shap_value]`` sorted by absolute
    importance descending.
    """
    try:
        import shap
    except ImportError as exc:
        raise RuntimeError(
            "shap is required for explainability. Install it with: uv pip install shap"
        ) from exc

    cols = feature_columns(history)
    X = history[cols].copy()

    if sample_size is not None and len(X) > sample_size:
        X_bg = X.sample(n=sample_size, random_state=42)
    else:
        X_bg = X

    # Access underlying models via forecaster internals.
    # LightGBMForecaster exposes model_rev and model_cogs.
    if not hasattr(forecaster, "model_rev") or not hasattr(forecaster, "model_cogs"):
        raise RuntimeError(
            "SHAP explainer currently supports forecasters with "
            "model_rev and model_cogs attributes."
        )

    out: dict[str, pd.DataFrame] = {}
    for target, model in (
        ("revenue", forecaster.model_rev),
        ("cogs", forecaster.model_cogs),
    ):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            explainer = shap.TreeExplainer(model)
            shap_values = explainer.shap_values(X_bg)

        mean_abs = pd.Series(
            shap_values.mean(axis=0) if shap_values.ndim == 2 else shap_values[0].mean(axis=0),
            index=cols,
        )
        mean_abs = mean_abs.abs().sort_values(ascending=False).reset_index()
        mean_abs.columns = ["feature", "mean_abs_shap"]
        out[target] = mean_abs

    return out
