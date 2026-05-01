"""CLI command to run Optuna hyperparameter tuning."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from datathon.commands.common import CommandError, ensure_no_unknown_args, take_option
from datathon.modeling.forecasters import list_forecasters
from datathon.modeling.tuner import run_study
from datathon.utils.config import load_modeling_config
from datathon.utils.console import console
from datathon.utils.data_loaders import load_training_data
from datathon.utils.help_texts import tune_help
from datathon.utils.paths import configs_dir, project_root, warehouse_path


@dataclass(frozen=True)
class TuneOptions:
    model_type: str
    warehouse: Path
    n_trials: int
    timeout: int | None
    n_folds: int
    horizon_days: int
    cv_type: str
    train_window_days: int
    purge_days: int
    output_path: Path
    storage: str | None
    seed: int
    config_path: Path | None


def parse_args(raw_args: list[str]) -> TuneOptions:
    args = list(raw_args)
    model_type = take_option(args, "--model-type", default="lightgbm")
    available = list_forecasters()
    if model_type not in available:
        raise CommandError(f"--model-type must be one of: {', '.join(available)}.")

    warehouse = Path(take_option(args, "--warehouse", default=str(warehouse_path())))
    n_trials = int(take_option(args, "--n-trials", default="50"))
    timeout_raw = take_option(args, "--timeout", default="")
    timeout = int(timeout_raw) if timeout_raw else None
    n_folds = int(take_option(args, "--n-folds", default="2"))
    horizon_days = int(take_option(args, "--horizon-days", default="548"))
    cv_type = take_option(args, "--cv-type", default="sliding")
    train_window_days = int(take_option(args, "--train-window-days", default="1096"))
    purge_days = int(take_option(args, "--purge-days", default="7"))
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

    config_path_raw = take_option(args, "--config", default="")
    config_path = Path(config_path_raw) if config_path_raw else None

    ensure_no_unknown_args(args)
    if cv_type not in ("expanding", "sliding"):
        raise CommandError("--cv-type must be 'expanding' or 'sliding'.")
    return TuneOptions(
        model_type=model_type,
        warehouse=warehouse,
        n_trials=n_trials,
        timeout=timeout,
        n_folds=n_folds,
        horizon_days=horizon_days,
        cv_type=cv_type,
        train_window_days=train_window_days,
        purge_days=purge_days,
        output_path=output_path,
        storage=storage,
        seed=seed,
        config_path=config_path,
    )


def print_help() -> None:
    console.print("[bold]tune[/bold]")
    console.print(tune_help())


def run(options: TuneOptions) -> None:
    config = load_modeling_config(options.config_path)
    df = load_training_data(config, options.warehouse)

    from datathon.utils.config import resolve_targets

    _, cogs_column, target_transform, _ = resolve_targets(config)
    console.print(
        f"Config: target_transform=[bold]{target_transform}[/bold] | "
        f"cogs_target=[bold]{cogs_column}[/bold] | "
        f"sequential_cogs=[bold]{config.get('sequential_cogs', False)}[/bold]"
    )

    storage = options.storage
    if storage is None:
        storage_path = project_root() / "optuna_studies" / f"{options.model_type}.db"
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        storage = f"sqlite:///{storage_path}"

    cv_label = f"{options.cv_type}"
    if options.cv_type == "sliding":
        cv_label += f" (train={options.train_window_days}d)"
    if options.purge_days > 0:
        cv_label += f" [purge={options.purge_days}d]"

    console.print(
        f"Tuning [bold]{options.model_type}[/bold] on [bold]{len(df)}[/bold] rows | "
        f"Trials: {options.n_trials} | CV: {options.n_folds}-fold × {options.horizon_days}d "
        f"({cv_label}) | Storage: {storage}"
    )

    try:
        best_params, best_mae, best_rmse, best_r2_rev, best_r2_cogs = run_study(
            df=df,
            model_type=options.model_type,
            n_trials=options.n_trials,
            timeout=options.timeout,
            n_folds=options.n_folds,
            horizon_days=options.horizon_days,
            cv_type=options.cv_type,
            train_window_days=options.train_window_days,
            purge_days=options.purge_days,
            seed=options.seed,
            storage=storage,
            config_path=options.config_path,
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]Tuning interrupted by user.[/yellow]")
        console.print(f"Study saved to {storage}. Resume with the same --storage URL.")
        return

    console.print(
        f"\n[green]Best Total MAE: {best_mae:,.0f}  |  RMSE: {best_rmse:,.0f}"
        f"  |  Rev R²: {best_r2_rev:.4f}  |  COGS R²: {best_r2_cogs:.4f}[/green]"
    )
    console.print("Best hyperparameters:")
    for k, v in sorted(best_params.items()):
        console.print(f"  {k}: {v}")

    delta = {"models": {options.model_type: best_params}}
    options.output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(options.output_path, "w") as f:
        yaml.dump(delta, f, sort_keys=False, allow_unicode=True)

    console.print(f"\nDelta config saved to [bold]{options.output_path}[/bold]")
    console.print(
        f"Use it with: [bold]datathon train --model-type {options.model_type} "
        f"--config {options.output_path} ...[/bold]"
    )
