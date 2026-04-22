"""CLI command to run SHAP explainability on trained forecasters."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rich.table import Table

from datathon.commands.common import CommandError, ensure_no_unknown_args, take_option
from datathon.modeling.explainer import explain_forecaster
from datathon.modeling.trainer import Trainer
from datathon.utils.console import console
from datathon.utils.data_loaders import load_modeling_data
from datathon.utils.paths import models_dir, reports_dir, warehouse_path


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


def run(options: ExplainOptions) -> None:
    if not options.model_dir.exists():
        raise CommandError(f"Model directory not found: {options.model_dir}")

    console.print(f"Loading artifacts from [bold]{options.model_dir}[/bold] …")
    forecaster, _feature_cols, _model_type, _cogs_col = Trainer.load_artifacts(options.model_dir)

    df = load_modeling_data(options.warehouse)
    console.print(f"Loaded [bold]{len(df)}[/bold] rows for background distribution.")

    console.print("\nRunning SHAP explainability …")
    results = explain_forecaster(
        forecaster=forecaster,
        history=df,
        output_dir=options.output_dir,
        sample_size=options.sample_size,
        max_display=options.max_display,
    )

    for target, shap_df in results.items():
        table = Table(title=f"Top {options.max_display} SHAP features — {target.capitalize()}")
        table.add_column("Rank", justify="right")
        table.add_column("Feature")
        table.add_column("Mean |SHAP|", justify="right")
        for rank, row in shap_df.head(options.max_display).iterrows():
            table.add_row(str(rank + 1), row["feature"], f"{row['mean_abs_shap']:,.2f}")
        console.print(table)

    console.print(f"\n[green]SHAP plots saved to {options.output_dir}[/green]")
