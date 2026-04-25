"""CLI command to generate submission predictions from trained models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from datathon.commands.common import CommandError, ensure_no_unknown_args, take_option
from datathon.modeling.forecasters import list_forecasters
from datathon.modeling.recursive import recursive_forecast
from datathon.modeling.trainer import Trainer
from datathon.tracking import MlflowTracker
from datathon.utils.competition import submission_columns
from datathon.utils.console import console
from datathon.utils.data_loaders import load_modeling_data, load_scaffold
from datathon.utils.paths import models_dir, submissions_dir, warehouse_path


@dataclass(frozen=True)
class PredictOptions:
    warehouse: Path
    model_type: str
    model_dir: Path
    output_path: Path


def parse_args(raw_args: list[str]) -> PredictOptions:
    args = list(raw_args)
    warehouse = Path(take_option(args, "--warehouse", default=str(warehouse_path())))
    model_type = take_option(args, "--model-type", default="lightgbm")
    available = list_forecasters()
    if model_type not in available:
        raise CommandError(f"--model-type must be one of: {', '.join(available)}.")

    model_dir = Path(
        take_option(
            args,
            "--model-dir",
            default=str(models_dir() / model_type),
        )
    )
    output_path = Path(
        take_option(
            args,
            "--output-path",
            default=str(submissions_dir() / f"{model_type}_submission.csv"),
        )
    )

    ensure_no_unknown_args(args)
    return PredictOptions(
        warehouse=warehouse,
        model_type=model_type,
        model_dir=model_dir,
        output_path=output_path,
    )


def print_help() -> None:
    console.print("[bold]predict[/bold]")
    console.print(
        "[dim]Usage:[/dim] datathon predict [--model-type <type>] "
        "[--warehouse <path>] [--model-dir <path>] [--output-path <path>]"
    )
    console.print("Load a trained model from disk and generate a submission CSV.")


def run(options: PredictOptions) -> None:
    if not options.model_dir.exists():
        raise CommandError(
            f"Model directory not found: {options.model_dir}. "
            "Run 'datathon train --mode train-final' first."
        )

    forecaster, feature_cols, model_type, cogs_column, residual_target = Trainer.load_artifacts(
        options.model_dir
    )
    cogs_is_ratio = cogs_column == "cogs_ratio"
    console.print(
        f"Loaded [bold]{model_type}[/bold] model from [bold]{options.model_dir}[/bold] "
        f"(COGS target: {cogs_column}, residual: {residual_target})"
    )

    history = load_modeling_data(options.warehouse)
    scaffold = load_scaffold(options.warehouse)
    console.print(
        f"History: [bold]{len(history)}[/bold] days | Scaffold: [bold]{len(scaffold)}[/bold] days"
    )

    predictions = recursive_forecast(
        forecaster=forecaster,
        history=history,
        scaffold=scaffold,
        feature_cols=feature_cols,
        cogs_is_ratio=cogs_is_ratio,
        residual_target=residual_target,
    )

    expected = submission_columns()
    submission = predictions.rename(
        columns={"date": expected[0], "revenue": expected[1], "cogs": expected[2]}
    )
    submission = submission[expected]

    options.output_path.parent.mkdir(parents=True, exist_ok=True)
    submission.to_csv(options.output_path, index=False)
    console.print(f"Submission written to [bold]{options.output_path}[/bold]")

    tracker = MlflowTracker(run_name=f"predict_{options.model_type}")
    with tracker:
        if tracker.enabled:
            tracker.log_param("model_type", model_type)
            tracker.log_param("history_days", len(history))
            tracker.log_param("forecast_days", len(scaffold))
            tracker.log_param("cogs_target", cogs_column)
            tracker.log_param("residual_target", residual_target)
            tracker.log_artifact(options.output_path)
            tracker.set_tag("status", "predicted")
