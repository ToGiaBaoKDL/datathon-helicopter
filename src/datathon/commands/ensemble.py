"""CLI command to generate an ensemble submission from trained models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from datathon.commands.common import CommandError, ensure_no_unknown_args, take_option
from datathon.modeling.forecasters import list_forecasters
from datathon.modeling.forecasters.ensemble import EnsembleForecaster
from datathon.modeling.recursive import direct_forecast, recursive_forecast
from datathon.modeling.trainer import Trainer
from datathon.utils.competition import submission_columns
from datathon.utils.config import load_modeling_config
from datathon.utils.console import console
from datathon.utils.data_loaders import load_scaffold, load_training_data
from datathon.utils.help_texts import ensemble_help
from datathon.utils.paths import models_dir, submissions_dir, warehouse_path


@dataclass(frozen=True)
class EnsembleOptions:
    warehouse: Path
    model_types: list[str]
    weights: list[float] | None
    model_dir: Path
    output_path: Path
    config_path: Path | None


def parse_args(raw_args: list[str]) -> EnsembleOptions:
    args = list(raw_args)
    warehouse = Path(take_option(args, "--warehouse", default=str(warehouse_path())))

    available = list_forecasters()
    default_models = ",".join(available[:3]) if len(available) >= 3 else ",".join(available)
    model_types_raw = take_option(args, "--model-types", default=default_models)
    model_types = [t.strip() for t in model_types_raw.split(",") if t.strip()]
    if len(model_types) < 2:
        raise CommandError("--model-types must contain at least 2 comma-separated model types.")

    model_dir = Path(take_option(args, "--model-dir", default=str(models_dir())))
    for mt in model_types:
        if mt not in available and not (model_dir / mt).exists():
            raise CommandError(
                f"--model-types contains unavailable model '{mt}'. "
                f"Available: {', '.join(available)}."
            )

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

    output_path = Path(
        take_option(
            args,
            "--output-path",
            default=str(submissions_dir() / "ensemble_submission.csv"),
        )
    )

    config_path_raw = take_option(args, "--config", default="")
    config_path = Path(config_path_raw) if config_path_raw else None

    ensure_no_unknown_args(args)
    return EnsembleOptions(
        warehouse=warehouse,
        model_types=model_types,
        weights=weights,
        model_dir=model_dir,
        output_path=output_path,
        config_path=config_path,
    )


def print_help() -> None:
    console.print("[bold]ensemble[/bold]")
    console.print(ensemble_help())


def run(options: EnsembleOptions) -> None:
    config = load_modeling_config(options.config_path)
    history = load_training_data(config, options.warehouse)
    scaffold = load_scaffold(options.warehouse)
    if config.get("promo_features", False):
        from datathon.utils.data_loaders import _apply_promo_features_to_scaffold

        scaffold = _apply_promo_features_to_scaffold(scaffold, options.warehouse)

    from datathon.utils.config import resolve_targets

    _, cogs_column, target_transform, _ = resolve_targets(config)
    console.print(
        f"Config: target_transform=[bold]{target_transform}[/bold] | "
        f"cogs_target=[bold]{cogs_column}[/bold] | "
        f"restart_horizon=[bold]{config.get('restart_horizon', 'null')}[/bold]"
    )
    console.print(
        f"History: [bold]{len(history)}[/bold] days | Scaffold: [bold]{len(scaffold)}[/bold] days"
    )

    members: list = []
    feature_cols: list[str] | None = None
    cogs_is_ratio = False
    target_transform = "identity"
    restart_horizon = None
    for model_type in options.model_types:
        model_path = options.model_dir / model_type
        if not model_path.exists():
            raise CommandError(
                f"Model directory not found: {model_path}. "
                f"Run 'datathon train --mode train-final --model-type {model_type}' first."
            )

        forecaster, cols, loaded_type, cogs_col, trans, _seq, _rh, _fm, _spk = (
            Trainer.load_artifacts(model_path)
        )
        members.append(forecaster)
        if feature_cols is None:
            feature_cols = cols
            cogs_is_ratio = cogs_col == "cogs_ratio"
            target_transform = trans
            restart_horizon = _rh
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

    forecast_mode = config.get("forecast_mode", "recursive")
    if forecast_mode == "direct":
        predictions = direct_forecast(
            forecaster=ensemble,
            history=history,
            scaffold=scaffold,
            feature_cols=feature_cols,
            cogs_is_ratio=cogs_is_ratio,
            target_transform=target_transform,
        )
    else:
        predictions = recursive_forecast(
            forecaster=ensemble,
            history=history,
            scaffold=scaffold,
            feature_cols=feature_cols,
            cogs_is_ratio=cogs_is_ratio,
            target_transform=target_transform,
            restart_horizon=restart_horizon,
        )

    expected = submission_columns()
    submission = predictions.rename(
        columns={"date": expected[0], "revenue": expected[1], "cogs": expected[2]}
    )
    submission = submission[expected]

    options.output_path.parent.mkdir(parents=True, exist_ok=True)
    submission.to_csv(options.output_path, index=False)
    console.print(f"Ensemble submission written to [bold]{options.output_path}[/bold]")
