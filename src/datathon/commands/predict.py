"""CLI command to generate submission predictions from trained models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from datathon.commands.common import CommandError, ensure_no_unknown_args, take_option
from datathon.modeling.forecasters import list_forecasters
from datathon.modeling.recursive import direct_forecast, recursive_forecast
from datathon.modeling.trainer import Trainer
from datathon.tracking import MlflowTracker
from datathon.utils.competition import submission_columns
from datathon.utils.config import load_modeling_config
from datathon.utils.console import console
from datathon.utils.data_loaders import load_scaffold, load_training_data
from datathon.utils.help_texts import predict_help
from datathon.utils.paths import models_dir, submissions_dir, warehouse_path


@dataclass(frozen=True)
class PredictOptions:
    warehouse: Path
    model_type: str
    model_dir: Path
    output_path: Path
    config_path: Path | None


def parse_args(raw_args: list[str]) -> PredictOptions:
    args = list(raw_args)
    warehouse = Path(take_option(args, "--warehouse", default=str(warehouse_path())))
    model_type = take_option(args, "--model-type", default="lightgbm")
    available = list_forecasters() + ["stacked"]
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

    config_path_raw = take_option(args, "--config", default="")
    config_path = Path(config_path_raw) if config_path_raw else None

    ensure_no_unknown_args(args)
    return PredictOptions(
        warehouse=warehouse,
        model_type=model_type,
        model_dir=model_dir,
        output_path=output_path,
        config_path=config_path,
    )


def print_help() -> None:
    console.print("[bold]predict[/bold]")
    console.print(predict_help())


def run(options: PredictOptions) -> None:
    if not options.model_dir.exists():
        raise CommandError(
            f"Model directory not found: {options.model_dir}. "
            "Run 'datathon train --mode train-final' first."
        )

    (
        forecaster,
        feature_cols,
        model_type,
        cogs_column,
        target_transform,
        _seq,
        _rh,
        forecast_mode,
        spike_classifier,
    ) = Trainer.load_artifacts(options.model_dir)
    cogs_is_ratio = cogs_column == "cogs_ratio"
    restart_horizon = _rh
    console.print(
        f"Loaded [bold]{model_type}[/bold] model from [bold]{options.model_dir}[/bold] "
        f"(COGS target: {cogs_column}, transform: {target_transform}, mode: {forecast_mode})"
    )

    config = load_modeling_config(options.config_path)
    history = load_training_data(config, options.warehouse)
    scaffold = load_scaffold(options.warehouse)

    if config.get("promo_features", False):
        from datathon.utils.data_loaders import _apply_promo_features_to_scaffold

        scaffold = _apply_promo_features_to_scaffold(scaffold, options.warehouse)

    console.print(
        f"Config: target_transform=[bold]{target_transform}[/bold] | "
        f"cogs_target=[bold]{cogs_column}[/bold] | "
        f"forecast_mode=[bold]{forecast_mode}[/bold] | "
        f"restart_horizon=[bold]{restart_horizon if restart_horizon is not None else 'null'}[/bold]"
    )
    console.print(
        f"History: [bold]{len(history)}[/bold] days | Scaffold: [bold]{len(scaffold)}[/bold] days"
    )

    if forecast_mode == "direct":
        predictions = direct_forecast(
            forecaster=forecaster,
            history=history,
            scaffold=scaffold,
            feature_cols=feature_cols,
            cogs_is_ratio=cogs_is_ratio,
            target_transform=target_transform,
        )
    else:
        predictions = recursive_forecast(
            forecaster=forecaster,
            history=history,
            scaffold=scaffold,
            feature_cols=feature_cols,
            cogs_is_ratio=cogs_is_ratio,
            target_transform=target_transform,
            restart_horizon=restart_horizon,
        )

    # Apply spike boost if a spike classifier was saved with the model
    if spike_classifier is not None:
        console.print("Applying spike boost …")
        # Re-construct future features from the scaffold to predict spike probability.
        from datathon.modeling.recursive import _prepare_future_frame

        future_frame = _prepare_future_frame(history, scaffold)

        # Merge promo features from scaffold (already computed for future dates)
        # into future_frame so the classifier sees the same features it was
        # trained on.
        promo_cols = [c for c in feature_cols if c.startswith("promo_")]
        if promo_cols and any(c in scaffold.columns for c in promo_cols):
            scaffold_indexed = scaffold.set_index("date")
            future_frame_indexed = future_frame.set_index("sales_date")
            for col in promo_cols:
                if col in scaffold_indexed.columns:
                    future_frame_indexed[col] = scaffold_indexed[col].values
            future_frame = future_frame_indexed.reset_index()

        static_cols = [c for c in feature_cols if c in future_frame.columns]
        if static_cols:
            spike_prob = spike_classifier.predict_proba(future_frame[static_cols])
            old_revenue = predictions["revenue"].to_numpy().copy()
            old_cogs = (
                predictions["cogs"].to_numpy().copy() if "cogs" in predictions.columns else None
            )
            predictions["revenue"] = spike_classifier.apply_boost(old_revenue, spike_prob)
            # Recompute COGS if ratio mode, otherwise keep original
            if cogs_is_ratio and old_cogs is not None:
                ratio = np.divide(
                    old_cogs,
                    old_revenue,
                    out=np.zeros_like(old_cogs),
                    where=old_revenue != 0,
                )
                ratio = np.clip(ratio, 0.0, 2.0)
                predictions["cogs"] = predictions["revenue"].to_numpy() * ratio
            console.print(f"  Spike boost applied (max boost: {spike_classifier.max_boost:.2f})")

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
            tracker.log_param("target_transform", target_transform)
            tracker.log_artifact(options.output_path)
            tracker.set_tag("status", "predicted")
