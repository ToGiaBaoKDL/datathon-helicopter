"""CLI command to train forecasting models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from rich.table import Table

from datathon.commands.common import CommandError, ensure_no_unknown_args, take_option
from datathon.modeling.baselines import seasonal_naive
from datathon.modeling.cv import ExpandingWindowCV, SlidingWindowCV, build_cv
from datathon.modeling.factory import build_forecaster
from datathon.modeling.forecasters import list_forecasters
from datathon.modeling.metrics import compute_metrics
from datathon.modeling.trainer import Trainer
from datathon.tracking import MlflowTracker
from datathon.utils.config import load_modeling_config, resolve_targets
from datathon.utils.console import console
from datathon.utils.data_loaders import load_training_data
from datathon.utils.help_texts import train_help
from datathon.utils.paths import models_dir, warehouse_path


@dataclass(frozen=True)
class TrainOptions:
    mode: str
    model_type: str
    warehouse: Path
    model_dir: Path
    n_folds: int
    horizon_days: int
    cv_type: str
    train_window_days: int
    purge_days: int
    config_path: Path | None


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

    n_folds = int(take_option(args, "--n-folds", default="2"))
    horizon_days = int(take_option(args, "--horizon-days", default="548"))
    cv_type = take_option(args, "--cv-type", default="sliding")
    train_window_days = int(take_option(args, "--train-window-days", default="1096"))
    purge_days = int(take_option(args, "--purge-days", default="7"))

    config_path_raw = take_option(args, "--config", default="")
    config_path = Path(config_path_raw) if config_path_raw else None

    ensure_no_unknown_args(args)
    if cv_type not in ("expanding", "sliding"):
        raise CommandError("--cv-type must be 'expanding' or 'sliding'.")
    return TrainOptions(
        mode=mode,
        model_type=model_type,
        warehouse=warehouse,
        model_dir=model_dir,
        n_folds=n_folds,
        horizon_days=horizon_days,
        cv_type=cv_type,
        train_window_days=train_window_days,
        purge_days=purge_days,
        config_path=config_path,
    )


def print_help() -> None:
    console.print("[bold]train[/bold]")
    console.print(train_help())
    console.print(
        f"[dim]Available model types:[/dim] {', '.join(list_forecasters())}\n"
        "[dim]evaluate[/dim]   Run cross-validation and print metrics.\n"
        "[dim]train-final[/dim] Train on full history and save model artifacts.\n"
        "[dim]--cv-type[/dim]      'sliding' (default) or 'expanding'.\n"
        "[dim]--train-window-days[/dim]  Training window for 'sliding' CV (default 1096).\n"
        "[dim]--purge-days[/dim]   Purge gap between train/val to reduce autocorrelation leakage.\n"
        "[dim]--config[/dim]   Optional modeling config path "
        "(defaults to configs/modeling.yaml)."
    )


def _evaluate_baseline_on_splits(
    df: pd.DataFrame,
    cv: ExpandingWindowCV | SlidingWindowCV,
) -> dict[str, list[dict[str, float]]]:
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
    cv_type: str,
) -> None:
    title = (
        f"{cv_type.capitalize()}-window CV metrics ({model_type.capitalize()} vs Seasonal Naive)"
    )
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
    config = load_modeling_config(options.config_path)
    df = load_training_data(config, options.warehouse)
    console.print(f"Loaded [bold]{len(df)}[/bold] rows | Model: [bold]{options.model_type}[/bold]")

    revenue_column, cogs_column, target_transform, cogs_is_ratio = resolve_targets(config)

    console.print(
        f"Config: target_transform=[bold]{target_transform}[/bold] | "
        f"cogs_target=[bold]{cogs_column}[/bold] | "
        f"sequential_cogs=[bold]{config.get('sequential_cogs', False)}[/bold] | "
        f"cv=[bold]{options.cv_type}[/bold] | "
        f"restart_horizon=[bold]{config.get('restart_horizon', 'null')}[/bold]"
    )

    forecaster = build_forecaster(options.model_type, config)
    cv = build_cv(
        options.n_folds,
        options.horizon_days,
        options.cv_type,
        options.train_window_days,
        options.purge_days,
    )
    forecast_mode = config.get("forecast_mode", "recursive")
    trainer = Trainer(
        forecaster=forecaster,
        cv=cv,
        cogs_column=cogs_column,
        target_transform=target_transform,
        forecast_mode=forecast_mode,
    )

    tracker = MlflowTracker(run_name=f"train_{options.model_type}_{options.mode}")
    with tracker:
        if tracker.enabled:
            tracker.log_param("model_type", options.model_type)
            tracker.log_param("mode", options.mode)
            tracker.log_param("cv_type", options.cv_type)
            tracker.log_param("n_folds", options.n_folds)
            tracker.log_param("horizon_days", options.horizon_days)
            tracker.log_param("purge_days", options.purge_days)
            tracker.log_config(config)

        restart_horizon = config.get("restart_horizon")

        if options.mode == "evaluate":
            model_results = trainer.run_cv(
                df, tracker=tracker, sample_weight=True, restart_horizon=restart_horizon
            )
            naive_results = _evaluate_baseline_on_splits(df, cv)
            _print_comparison(model_results, naive_results, options.model_type, options.cv_type)

            if tracker.enabled:
                tracker.set_tag("status", "evaluated")
        else:
            model_results = None

        if options.mode == "train-final":
            console.print("\nTraining final models on full history …")
            forecaster, feature_cols = trainer.train_final(df, sample_weight=True)

            spike_classifier = None
            if config.get("spike_classifier", False):
                console.print("Training spike classifier …")
                from datathon.modeling.spike_classifier import SpikeClassifier

                spike_classifier = SpikeClassifier()
                spike_classifier.fit(df[feature_cols], df["revenue"])
                console.print(
                    f"  Spike threshold: {spike_classifier.threshold_:,.0f} | "
                    f"Empirical boost: {spike_classifier.empirical_boost_:.3f}"
                )

            Trainer.save_artifacts(
                model_dir=options.model_dir,
                forecaster=forecaster,
                feature_cols=feature_cols,
                model_type=options.model_type,
                cv_results=model_results,
                cogs_column=cogs_column,
                target_transform=target_transform,
                sequential_cogs=config.get("sequential_cogs", False),
                restart_horizon=config.get("restart_horizon"),
                forecast_mode=forecast_mode,
                spike_classifier=spike_classifier,
            )
            console.print(f"Artifacts saved to [bold]{options.model_dir}[/bold]")

            if tracker.enabled:
                tracker.log_model(options.model_dir, artifact_path="model")
                tracker.log_artifact(options.model_dir / "meta.json")
                tracker.set_tag("status", "trained_final")
