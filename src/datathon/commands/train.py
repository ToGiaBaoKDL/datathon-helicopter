"""CLI command to train forecasting models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from rich.table import Table

from datathon.commands.common import CommandError, ensure_no_unknown_args, take_option
from datathon.modeling.baselines import compute_metrics, seasonal_naive
from datathon.modeling.cv import ExpandingWindowCV
from datathon.modeling.factory import build_forecaster
from datathon.modeling.forecasters import list_forecasters
from datathon.modeling.trainer import Trainer
from datathon.utils.config import load_modeling_config
from datathon.utils.console import console
from datathon.utils.data_loaders import load_forecast_base, load_modeling_data
from datathon.utils.paths import models_dir, warehouse_path


@dataclass(frozen=True)
class TrainOptions:
    mode: str
    model_type: str
    warehouse: Path
    model_dir: Path
    n_folds: int
    horizon_days: int


def parse_args(raw_args: list[str]) -> TrainOptions:
    args = list(raw_args)
    mode = take_option(args, "--mode", default="evaluate")
    if mode not in {"evaluate", "train-final"}:
        raise CommandError("--mode must be one of: evaluate, train-final.")

    model_type = take_option(args, "--model-type", default="lightgbm")
    available = list_forecasters()
    if model_type not in available:
        raise CommandError(f"--model-type must be one of: {', '.join(available)}.")

    warehouse = Path(take_option(args, "--warehouse", default=str(warehouse_path())))
    model_dir = Path(
        take_option(
            args,
            "--model-dir",
            default=str(models_dir() / model_type),
        )
    )

    n_folds = int(take_option(args, "--n-folds", default="5"))
    horizon_days = int(take_option(args, "--horizon-days", default="30"))

    ensure_no_unknown_args(args)
    return TrainOptions(
        mode=mode,
        model_type=model_type,
        warehouse=warehouse,
        model_dir=model_dir,
        n_folds=n_folds,
        horizon_days=horizon_days,
    )


def print_help() -> None:
    console.print("[bold]train[/bold]")
    console.print(
        "[dim]Usage:[/dim] datathon train --mode <evaluate|train-final> "
        "[--model-type <type>] [--warehouse <path>] [--model-dir <path>] "
        "[--n-folds <int>] [--horizon-days <int>]"
    )
    console.print(
        f"[dim]Available model types:[/dim] {', '.join(list_forecasters())}\n"
        "[dim]evaluate[/dim]   Run expanding-window CV and print metrics.\n"
        "[dim]train-final[/dim] Train on full history and save model artifacts."
    )


def _evaluate_baseline_on_splits(
    df: pd.DataFrame,
    n_folds: int,
    horizon_days: int,
) -> dict[str, list[dict[str, float]]]:
    cv = ExpandingWindowCV(n_folds=n_folds, horizon_days=horizon_days)
    results: dict[str, list[dict[str, float]]] = {"revenue": [], "cogs": []}

    for _fold, train_idx, val_idx in cv.split(df):
        train_df = df.iloc[train_idx]
        val_df = df.iloc[val_idx]

        for target in ("revenue", "cogs"):
            preds = seasonal_naive(
                train_series=train_df[target],
                horizon=len(val_df),
                seasonal_period=7,
            )
            y_true = val_df[target].to_numpy()
            metrics = compute_metrics(y_true, preds)
            results[target].append(
                {
                    "fold": _fold + 1,
                    "mae": metrics["mae"],
                    "rmse": metrics["rmse"],
                    "r2": metrics["r2"],
                }
            )

    return results


def _print_comparison(
    model_results: dict,
    naive_results: dict,
    model_type: str,
) -> None:
    title = f"Expanding-window CV metrics ({model_type.capitalize()} vs Seasonal Naive)"
    table = Table(title=title)
    table.add_column("Target")
    table.add_column("Fold")
    table.add_column(f"{model_type.capitalize()} MAE", justify="right")
    table.add_column("Naive MAE", justify="right")
    table.add_column(f"{model_type.capitalize()} RMSE", justify="right")
    table.add_column("Naive RMSE", justify="right")

    for target in ("revenue", "cogs"):
        for model_fold, naive_fold in zip(
            model_results[target], naive_results[target], strict=True
        ):
            table.add_row(
                target.capitalize(),
                str(model_fold["fold"]),
                f"{model_fold['mae']:,.0f}",
                f"{naive_fold['mae']:,.0f}",
                f"{model_fold['rmse']:,.0f}",
                f"{naive_fold['rmse']:,.0f}",
            )

    console.print(table)


def run(options: TrainOptions) -> None:
    df = load_modeling_data(options.warehouse)
    console.print(f"Loaded [bold]{len(df)}[/bold] rows | Model: [bold]{options.model_type}[/bold]")

    config = load_modeling_config()
    forecaster = build_forecaster(options.model_type, config)
    cv = ExpandingWindowCV(n_folds=options.n_folds, horizon_days=options.horizon_days)
    trainer = Trainer(forecaster=forecaster, cv=cv)

    if options.mode == "evaluate":
        model_results = trainer.run_cv(df)
        base_df = load_forecast_base(options.warehouse)
        naive_results = _evaluate_baseline_on_splits(base_df, options.n_folds, options.horizon_days)
        _print_comparison(model_results, naive_results, options.model_type)
    else:
        model_results = None

    if options.mode == "train-final":
        console.print("\nTraining final models on full history …")
        forecaster, feature_cols = trainer.train_final(df)
        Trainer.save_artifacts(
            model_dir=options.model_dir,
            forecaster=forecaster,
            feature_cols=feature_cols,
            model_type=options.model_type,
            cv_results=model_results,
        )
        console.print(f"Artifacts saved to [bold]{options.model_dir}[/bold]")
