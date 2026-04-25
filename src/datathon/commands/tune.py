"""CLI command to run Optuna hyperparameter tuning."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from datathon.commands.common import CommandError, ensure_no_unknown_args, take_option
from datathon.modeling.forecasters import list_forecasters
from datathon.modeling.tuner import run_study
from datathon.utils.console import console
from datathon.utils.data_loaders import load_modeling_data
from datathon.utils.paths import configs_dir, project_root, warehouse_path


@dataclass(frozen=True)
class TuneOptions:
    model_type: str
    warehouse: Path
    n_trials: int
    timeout: int | None
    n_folds: int
    horizon_days: int
    output_path: Path
    storage: str | None
    seed: int
    patience: int
    config_path: Path | None


def parse_args(raw_args: list[str]) -> TuneOptions:
    args = list(raw_args)
    model_type = take_option(args, "--model-type", default="catboost")
    available = list_forecasters()
    if model_type not in available:
        raise CommandError(f"--model-type must be one of: {', '.join(available)}.")

    warehouse = Path(take_option(args, "--warehouse", default=str(warehouse_path())))
    n_trials = int(take_option(args, "--n-trials", default="50"))
    timeout_raw = take_option(args, "--timeout", default="")
    timeout = int(timeout_raw) if timeout_raw else None
    n_folds = int(take_option(args, "--n-folds", default="2"))
    horizon_days = int(take_option(args, "--horizon-days", default="548"))
    output_path = Path(
        take_option(
            args,
            "--output-path",
            default=str(configs_dir() / "tuned" / f"{model_type}.yaml"),
        )
    )
    storage_raw = take_option(args, "--storage", default="")
    storage = storage_raw if storage_raw else None
    seed = int(take_option(args, "--seed", default="42"))
    patience = int(take_option(args, "--patience", default="10"))

    config_path_raw = take_option(args, "--config", default="")
    config_path = Path(config_path_raw) if config_path_raw else None

    ensure_no_unknown_args(args)
    return TuneOptions(
        model_type=model_type,
        warehouse=warehouse,
        n_trials=n_trials,
        timeout=timeout,
        n_folds=n_folds,
        horizon_days=horizon_days,
        output_path=output_path,
        storage=storage,
        seed=seed,
        patience=patience,
        config_path=config_path,
    )


def print_help() -> None:
    console.print("[bold]tune[/bold]")
    console.print(
        "[dim]Usage:[/dim] datathon tune [--model-type <type>] [--n-trials <int>] "
        "[--timeout <sec>] [--n-folds <int>] [--horizon-days <int>] "
        "[--output-path <path>] [--storage <url>] [--seed <int>] "
        "[--patience <int>] [--config <path>]"
    )
    console.print(
        "Run Optuna hyperparameter search for a single model type.\n"
        "Best params are written as a delta config (only the tuned model's "
        "hyperparameters).  Pass the delta to train/predict/compare via --config.\n"
        "Use --storage sqlite:///path/to/db.sqlite3 to resume interrupted studies."
    )


def run(options: TuneOptions) -> None:
    df = load_modeling_data(options.warehouse)
    storage = options.storage
    if storage is None:
        storage_path = project_root() / "optuna_studies" / f"{options.model_type}.db"
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        storage = f"sqlite:///{storage_path}"

    console.print(
        f"Tuning [bold]{options.model_type}[/bold] on [bold]{len(df)}[/bold] rows | "
        f"Trials: {options.n_trials} | CV: {options.n_folds}-fold × {options.horizon_days}d | "
        f"Patience: {options.patience} | Storage: {storage}"
    )

    try:
        best_params, best_mae = run_study(
            df=df,
            model_type=options.model_type,
            n_trials=options.n_trials,
            timeout=options.timeout,
            n_folds=options.n_folds,
            horizon_days=options.horizon_days,
            seed=options.seed,
            storage=storage,
            patience=options.patience,
            config_path=options.config_path,
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]Tuning interrupted by user.[/yellow]")
        console.print(f"Study saved to {storage}. Resume with the same --storage URL.")
        return

    console.print(f"\n[green]Best Total MAE: {best_mae:,.0f}[/green]")
    console.print("Best hyperparameters:")
    for k, v in sorted(best_params.items()):
        console.print(f"  {k}: {v}")

    # Write delta config (only the tuned model's subtree).
    delta = {"models": {options.model_type: best_params}}
    options.output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(options.output_path, "w") as f:
        yaml.dump(delta, f, sort_keys=False, allow_unicode=True)

    console.print(f"\nDelta config saved to [bold]{options.output_path}[/bold]")
    console.print(
        f"Use it with: [bold]datathon train --model-type {options.model_type} "
        f"--config {options.output_path} ...[/bold]"
    )
