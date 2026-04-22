"""SHAP explainability for forecasters."""

from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd

from datathon.modeling.forecasters.base import BaseForecaster
from datathon.modeling.recursive import feature_columns

matplotlib.use("Agg")


def _save_shap_plots(
    shap_values,
    X_bg: pd.DataFrame,
    target: str,
    output_dir: Path,
    max_display: int,
) -> None:
    """Save beeswarm summary and bar plots for a target."""
    import shap as shap_lib

    if isinstance(shap_values, list):
        shap_values = shap_values[0]

    output_dir.mkdir(parents=True, exist_ok=True)

    # Summary (beeswarm)
    fig = plt.figure(figsize=(10, max_display * 0.4 + 2))
    shap_lib.summary_plot(
        shap_values,
        X_bg,
        max_display=max_display,
        show=False,
        plot_size=None,
    )
    plt.tight_layout()
    fig.savefig(output_dir / f"{target}_summary.png", dpi=200, bbox_inches="tight")
    plt.close(fig)

    # Bar plot
    fig = plt.figure(figsize=(10, max_display * 0.4 + 2))
    shap_lib.summary_plot(
        shap_values,
        X_bg,
        plot_type="bar",
        max_display=max_display,
        show=False,
        plot_size=None,
    )
    plt.tight_layout()
    fig.savefig(output_dir / f"{target}_bar.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def explain_forecaster(
    forecaster: BaseForecaster,
    history: pd.DataFrame,
    output_dir: Path | None = None,
    sample_size: int | None = 500,
    max_display: int = 20,
) -> dict[str, pd.DataFrame]:
    """Run SHAP explainability on a fitted forecaster.

    Parameters
    ----------
    forecaster:
        A fitted ``BaseForecaster`` with ``model_rev`` and ``model_cogs``.
    history:
        Historical dataframe used for background distribution.
    output_dir:
        If provided, saves beeswarm and bar plots per target.
    sample_size:
        Number of rows to sample for the background dataset.
        ``None`` uses the full history.
    max_display:
        Maximum features to show in plots.

    Returns
    -------
    Mapping of ``{"revenue": shap_df, "cogs": shap_df}`` where each
    DataFrame has columns ``[feature, mean_abs_shap]`` sorted descending.
    """
    try:
        import shap as shap_lib
    except ImportError as exc:
        raise RuntimeError(
            "shap is required for explainability. Install it with: uv pip install shap"
        ) from exc

    if not hasattr(forecaster, "model_rev") or not hasattr(forecaster, "model_cogs"):
        raise RuntimeError(
            "SHAP explainer currently supports forecasters with "
            "model_rev and model_cogs attributes."
        )

    cols = feature_columns(history)
    X = history[cols].copy()

    X_bg = (
        X.sample(n=sample_size, random_state=42)
        if sample_size is not None and len(X) > sample_size
        else X
    )

    out: dict[str, pd.DataFrame] = {}
    for target, model in (
        ("revenue", forecaster.model_rev),
        ("cogs", forecaster.model_cogs),
    ):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            explainer = shap_lib.TreeExplainer(model)
            shap_values = explainer.shap_values(X_bg)

        if output_dir is not None:
            _save_shap_plots(shap_values, X_bg, target, output_dir, max_display)

        if isinstance(shap_values, list):
            shap_values = shap_values[0]
        mean_abs = pd.Series(shap_values.mean(axis=0), index=cols)
        mean_abs = mean_abs.abs().sort_values(ascending=False).reset_index()
        mean_abs.columns = ["feature", "mean_abs_shap"]
        out[target] = mean_abs

    return out
