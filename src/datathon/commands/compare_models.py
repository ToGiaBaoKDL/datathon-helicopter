"""CLI command to compare all registered forecasters and pick the best one."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from datathon.commands.common import ensure_no_unknown_args, take_option
from datathon.modeling.cv import ExpandingWindowCV
from datathon.modeling.factory import build_forecaster
from datathon.modeling.forecasters import list_forecasters
from datathon.modeling.recursive import recursive_forecast
from datathon.modeling.trainer import Trainer
from datathon.utils.competition import submission_columns
from datathon.utils.config import load_modeling_config
from datathon.utils.console import console
from datathon.utils.data_loaders import load_modeling_data, load_scaffold
from datathon.utils.paths import models_dir, submissions_dir, warehouse_path


@dataclass(frozen=True)
class CompareOptions:
    warehouse: Path
    n_folds: int
    horizon_days: int
    model_dir: Path
    output_path: Path


def parse_args(raw_args: list[str]) -> CompareOptions:
    args = list(raw_args)
    warehouse = Path(take_option(args, "--warehouse", default=str(warehouse_path())))
    n_folds = int(take_option(args, "--n-folds", default="5"))
    horizon_days = int(take_option(args, "--horizon-days", default="30"))
    model_dir = Path(take_option(args, "--model-dir", default=str(models_dir())))
    output_path = Path(
        take_option(
            args,
            "--output-path",
            default=str(submissions_dir() / "best_submission.csv"),
        )
    )
    ensure_no_unknown_args(args)
    return CompareOptions(
        warehouse=warehouse,
        n_folds=n_folds,
        horizon_days=horizon_days,
        model_dir=model_dir,
        output_path=output_path,
    )


def print_help() -> None:
    console.print("[bold]compare-models[/bold]")
    console.print(
        "[dim]Usage:[/dim] datathon compare-models [--warehouse <path>] "
        "[--n-folds <int>] [--horizon-days <int>] [--model-dir <path>] "
        "[--output-path <path>]"
    )
    console.print(
        "Runs expanding-window CV for every registered model type, "
        "picks the winner by lowest average MAE, trains a final model, "
        "and generates a submission."
    )


def _run_comparison(
    df: pd.DataFrame,
    config: dict[str, Any],
    n_folds: int,
    horizon_days: int,
) -> tuple[str, dict[str, dict[str, list[dict[str, float]]]]]:
    """Run CV for all models and return (winner_type, all_results)."""
    cv = ExpandingWindowCV(n_folds=n_folds, horizon_days=horizon_days)
    all_results: dict[str, dict[str, list[dict[str, float]]]] = {}
    scores: dict[str, float] = {}

    available = list_forecasters()
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for model_type in available:
            task = progress.add_task(f"Evaluating {model_type} …", total=None)
            forecaster = build_forecaster(model_type, config)
            trainer = Trainer(forecaster=forecaster, cv=cv)
            results = trainer.run_cv(df)
            all_results[model_type] = results

            avg_rev_mae = sum(r["mae"] for r in results["revenue"]) / len(results["revenue"])
            avg_cogs_mae = sum(r["mae"] for r in results["cogs"]) / len(results["cogs"])
            scores[model_type] = avg_rev_mae + avg_cogs_mae
            progress.update(
                task,
                description=(
                    f"[green]{model_type}[/green] — "
                    f"Rev MAE {avg_rev_mae:,.0f} | COGS MAE {avg_cogs_mae:,.0f}"
                ),
            )

    winner = min(scores, key=scores.get)
    return winner, all_results


def _print_summary(
    all_results: dict[str, dict[str, list[dict[str, float]]]],
    winner: str,
) -> None:
    table = Table(title="Model Comparison (Average MAE)")
    table.add_column("Model")
    table.add_column("Revenue MAE", justify="right")
    table.add_column("COGS MAE", justify="right")
    table.add_column("Total MAE", justify="right")

    for model_type, results in all_results.items():
        avg_rev = sum(r["mae"] for r in results["revenue"]) / len(results["revenue"])
        avg_cogs = sum(r["mae"] for r in results["cogs"]) / len(results["cogs"])
        total = avg_rev + avg_cogs
        marker = " ★" if model_type == winner else ""
        table.add_row(
            model_type + marker,
            f"{avg_rev:,.0f}",
            f"{avg_cogs:,.0f}",
            f"{total:,.0f}",
        )

    console.print(table)


def run(options: CompareOptions) -> None:
    df = load_modeling_data(options.warehouse)
    config = load_modeling_config()

    console.print(
        f"Comparing [bold]{len(list_forecasters())}[/bold] model types on "
        f"[bold]{len(df)}[/bold] rows …"
    )

    winner, all_results = _run_comparison(df, config, options.n_folds, options.horizon_days)
    _print_summary(all_results, winner)

    console.print("\nTraining final models on full history …")
    for model_type in all_results:
        model_dir = options.model_dir / model_type
        if model_dir.exists():
            console.print(f"  [dim]{model_type}: already exists at {model_dir}, skipping.[/dim]")
            continue
        forecaster = build_forecaster(model_type, config)
        trainer = Trainer(forecaster=forecaster, cv=ExpandingWindowCV())
        forecaster_fitted, feature_cols = trainer.train_final(df)
        Trainer.save_artifacts(
            model_dir=model_dir,
            forecaster=forecaster_fitted,
            feature_cols=feature_cols,
            model_type=model_type,
            cv_results=all_results[model_type],
        )
        console.print(f"  [green]{model_type}[/green] saved to {model_dir}")

    # Load winner for best submission
    winner_dir = options.model_dir / winner
    winner_fitted, feature_cols, _ = Trainer.load_artifacts(winner_dir)

    # Generate winner submission
    scaffold = load_scaffold(options.warehouse)
    predictions = recursive_forecast(
        forecaster=winner_fitted,
        history=df,
        scaffold=scaffold,
        feature_cols=feature_cols,
    )

    expected = submission_columns()
    submission = predictions.rename(
        columns={"date": expected[0], "revenue": expected[1], "cogs": expected[2]}
    )
    submission = submission[expected]

    options.output_path.parent.mkdir(parents=True, exist_ok=True)
    submission.to_csv(options.output_path, index=False)
    console.print(f"Best submission written to [bold]{options.output_path}[/bold]")
