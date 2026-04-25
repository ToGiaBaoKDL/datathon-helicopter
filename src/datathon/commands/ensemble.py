"""CLI command to generate an ensemble submission from trained models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from datathon.commands.common import CommandError, ensure_no_unknown_args, take_option
from datathon.modeling.forecasters.ensemble import EnsembleForecaster
from datathon.modeling.recursive import recursive_forecast
from datathon.modeling.trainer import Trainer
from datathon.utils.competition import submission_columns
from datathon.utils.console import console
from datathon.utils.data_loaders import load_modeling_data, load_scaffold
from datathon.utils.paths import models_dir, submissions_dir, warehouse_path


@dataclass(frozen=True)
class EnsembleOptions:
    warehouse: Path
    model_types: list[str]
    weights: list[float] | None
    model_dir: Path
    output_path: Path


def parse_args(raw_args: list[str]) -> EnsembleOptions:
    args = list(raw_args)
    warehouse = Path(take_option(args, "--warehouse", default=str(warehouse_path())))
    model_types_raw = take_option(args, "--model-types", default="lightgbm,xgboost,catboost")
    model_types = [t.strip() for t in model_types_raw.split(",") if t.strip()]
    if len(model_types) < 2:
        raise CommandError("--model-types must contain at least 2 comma-separated model types.")

    weights_raw = take_option(args, "--weights", default="")
    weights: list[float] | None = None
    if weights_raw:
        try:
            weights = [float(w.strip()) for w in weights_raw.split(",") if w.strip()]
        except ValueError as exc:
            raise CommandError("--weights must be comma-separated floats.") from exc
        if len(weights) != len(model_types):
            raise CommandError(
                f"--weights must have {len(model_types)} values (one per model), "
                f"got {len(weights)}."
            )

    model_dir = Path(take_option(args, "--model-dir", default=str(models_dir())))
    output_path = Path(
        take_option(
            args,
            "--output-path",
            default=str(submissions_dir() / "ensemble_submission.csv"),
        )
    )

    ensure_no_unknown_args(args)
    return EnsembleOptions(
        warehouse=warehouse,
        model_types=model_types,
        weights=weights,
        model_dir=model_dir,
        output_path=output_path,
    )


def print_help() -> None:
    console.print("[bold]ensemble[/bold]")
    console.print(
        "[dim]Usage:[/dim] datathon ensemble [--model-types <t1,t2,...>] "
        "[--weights <w1,w2,...>] [--warehouse <path>] [--model-dir <path>] "
        "[--output-path <path>]"
    )
    console.print(
        "Load multiple trained models, average their predictions (optionally weighted), "
        "and generate a submission.\n"
        "Default models: lightgbm,xgboost,catboost | Default weights: equal"
    )


def run(options: EnsembleOptions) -> None:
    history = load_modeling_data(options.warehouse)
    scaffold = load_scaffold(options.warehouse)
    console.print(
        f"History: [bold]{len(history)}[/bold] days | Scaffold: [bold]{len(scaffold)}[/bold] days"
    )

    members: list = []
    feature_cols: list[str] | None = None
    cogs_is_ratio = False
    residual_target = False
    for model_type in options.model_types:
        model_path = options.model_dir / model_type
        if not model_path.exists():
            raise CommandError(
                f"Model directory not found: {model_path}. "
                f"Run 'datathon train --mode train-final --model-type {model_type}' first."
            )

        forecaster, cols, loaded_type, cogs_col, res_target = Trainer.load_artifacts(model_path)
        members.append(forecaster)
        if feature_cols is None:
            feature_cols = cols
            cogs_is_ratio = cogs_col == "cogs_ratio"
            residual_target = res_target
        elif cols != feature_cols:
            raise CommandError(
                f"Feature mismatch: {model_type} has {len(cols)} features, "
                f"expected {len(feature_cols)}."
            )
        console.print(f"Loaded [bold]{loaded_type}[/bold] from {model_path}")

    ensemble = EnsembleForecaster(members=members, weights=options.weights)
    weight_desc = (
        "equal" if options.weights is None else ",".join(f"{w:.2f}" for w in options.weights)
    )
    console.print(
        f"\nEnsemble of [bold]{len(members)}[/bold] models ready "
        f"(weights: {weight_desc}). Generating predictions …"
    )

    predictions = recursive_forecast(
        forecaster=ensemble,
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
    console.print(f"Ensemble submission written to [bold]{options.output_path}[/bold]")
