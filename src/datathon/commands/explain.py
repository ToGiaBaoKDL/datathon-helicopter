"""CLI command to run SHAP explainability on trained forecasters."""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from rich.table import Table

from datathon.commands.common import CommandError, ensure_no_unknown_args, take_option
from datathon.modeling.recursive import feature_columns
from datathon.modeling.trainer import Trainer
from datathon.utils.console import console
from datathon.utils.data_loaders import load_modeling_data
from datathon.utils.paths import models_dir, reports_dir, warehouse_path

matplotlib.use("Agg")
sns.set_theme(style="whitegrid", context="paper", palette="deep")


@dataclass(frozen=True)
class ExplainOptions:
    model_type: str
    model_dir: Path
    warehouse: Path
    output_dir: Path
    sample_size: int
    max_display: int


def parse_args(raw_args: list[str]) -> ExplainOptions:
    args = list(raw_args)
    model_type = take_option(args, "--model-type", default="lightgbm")
    warehouse = Path(take_option(args, "--warehouse", default=str(warehouse_path())))
    model_dir = Path(
        take_option(
            args,
            "--model-dir",
            default=str(models_dir() / model_type),
        )
    )
    output_dir = Path(
        take_option(
            args,
            "--output-dir",
            default=str(reports_dir() / "shap"),
        )
    )
    sample_size = int(take_option(args, "--sample-size", default="500"))
    max_display = int(take_option(args, "--max-display", default="20"))

    ensure_no_unknown_args(args)
    return ExplainOptions(
        model_type=model_type,
        model_dir=model_dir,
        warehouse=warehouse,
        output_dir=output_dir,
        sample_size=sample_size,
        max_display=max_display,
    )


def print_help() -> None:
    console.print("[bold]explain[/bold]")
    console.print(
        "[dim]Usage:[/dim] datathon explain [--model-type <type>] [--warehouse <path>] "
        "[--model-dir <path>] [--output-dir <path>] [--sample-size <int>] [--max-display <int>]"
    )
    console.print(
        "Generate SHAP summary and bar plots for a trained forecaster.\n"
        "Plots are saved as PNGs under [dim]<output-dir>/[/dim]."
    )


def _save_shap_plots(
    shap_values,
    X_bg: pd.DataFrame,
    target: str,
    output_dir: Path,
    max_display: int,
) -> None:
    """Save beeswarm summary and bar plots for a target."""
    import shap

    output_dir.mkdir(parents=True, exist_ok=True)

    # Summary (beeswarm)
    fig = plt.figure(figsize=(10, max_display * 0.4 + 2))
    shap.summary_plot(
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
    shap.summary_plot(
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


def run(options: ExplainOptions) -> None:
    if not options.model_dir.exists():
        raise CommandError(f"Model directory not found: {options.model_dir}")

    console.print(f"Loading artifacts from [bold]{options.model_dir}[/bold] …")
    forecaster, feature_cols, _model_type = Trainer.load_artifacts(options.model_dir)

    df = load_modeling_data(options.warehouse)
    console.print(f"Loaded [bold]{len(df)}[/bold] rows for background distribution.")

    cols = feature_columns(df)
    X = df[cols].copy()

    X_bg = (
        X.sample(n=options.sample_size, random_state=42)
        if options.sample_size is not None and len(X) > options.sample_size
        else X
    )

    if not hasattr(forecaster, "model_rev") or not hasattr(forecaster, "model_cogs"):
        raise CommandError(
            "SHAP explainer currently supports forecasters with "
            "model_rev and model_cogs attributes."
        )

    import shap

    for target, model in (
        ("revenue", forecaster.model_rev),
        ("cogs", forecaster.model_cogs),
    ):
        console.print(f"\nExplaining [bold]{target}[/bold] model …")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            explainer = shap.TreeExplainer(model)
            shap_values = explainer.shap_values(X_bg)

        _save_shap_plots(
            shap_values,
            X_bg,
            target,
            options.output_dir,
            options.max_display,
        )

        if isinstance(shap_values, list):
            shap_values = shap_values[0]
        mean_abs = pd.Series(shap_values.mean(axis=0), index=cols)
        top = mean_abs.abs().sort_values(ascending=False).head(options.max_display)

        table = Table(title=f"Top {options.max_display} SHAP features — {target.capitalize()}")
        table.add_column("Rank", justify="right")
        table.add_column("Feature")
        table.add_column("Mean |SHAP|", justify="right")
        for rank, (feature, value) in enumerate(top.items(), start=1):
            table.add_row(str(rank), feature, f"{value:,.2f}")
        console.print(table)

    console.print(f"\n[green]SHAP plots saved to {options.output_dir}[/green]")
