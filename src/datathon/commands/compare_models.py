"""CLI command to compare all registered forecasters and pick the best one."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from datathon.commands.common import ensure_no_unknown_args, take_option
from datathon.modeling.cv import ExpandingWindowCV
from datathon.modeling.factory import build_forecaster
from datathon.modeling.forecasters import list_forecasters
from datathon.modeling.forecasters.ensemble import EnsembleForecaster
from datathon.modeling.recursive import recursive_forecast
from datathon.modeling.trainer import Trainer
from datathon.utils.competition import submission_columns
from datathon.utils.config import load_modeling_config, resolve_targets
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
    config_path: Path | None
    force: bool


def parse_args(raw_args: list[str]) -> CompareOptions:
    args = list(raw_args)
    warehouse = Path(take_option(args, "--warehouse", default=str(warehouse_path())))
    n_folds = int(take_option(args, "--n-folds", default="2"))
    horizon_days = int(take_option(args, "--horizon-days", default="548"))
    model_dir = Path(take_option(args, "--model-dir", default=str(models_dir())))
    output_path = Path(
        take_option(
            args,
            "--output-path",
            default=str(submissions_dir() / "best_submission.csv"),
        )
    )
    config_path_raw = take_option(args, "--config", default="")
    config_path = Path(config_path_raw) if config_path_raw else None
    force = take_option(args, "--force", default="false").lower() in ("true", "1", "yes")

    ensure_no_unknown_args(args)
    return CompareOptions(
        warehouse=warehouse,
        n_folds=n_folds,
        horizon_days=horizon_days,
        model_dir=model_dir,
        output_path=output_path,
        config_path=config_path,
        force=force,
    )


def print_help() -> None:
    console.print("[bold]compare-models[/bold]")
    console.print(
        "[dim]Usage:[/dim] datathon compare-models [--warehouse <path>] "
        "[--n-folds <int>] [--horizon-days <int>] [--model-dir <path>] "
        "[--output-path <path>] [--config <path>] [--force]"
    )
    console.print(
        "Runs expanding-window CV for every registered model type, "
        "evaluates a weighted ensemble (inverse MAE), "
        "picks the winner by lowest average MAE, trains finals, "
        "and generates a submission from the true winner.\n"
        "[dim]--config[/dim]   Optional modeling config path "
        "(defaults to configs/modeling.yaml).\n"
        "[dim]--force[/dim]    Retrain final models even if artifacts already exist."
    )


def _run_comparison(
    df: pd.DataFrame,
    config: dict[str, Any],
    n_folds: int,
    horizon_days: int,
    cogs_column: str = "cogs",
    residual_target: bool = False,
) -> tuple[str, dict, dict[str, list[pd.DataFrame]], list[float]]:
    """Run CV for all models, compute weighted ensemble CV."""
    cv = ExpandingWindowCV(n_folds=n_folds, horizon_days=horizon_days)
    all_results: dict[str, dict[str, list[dict[str, float]]]] = {}
    all_preds: dict[str, list[pd.DataFrame]] = {}
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
            trainer = Trainer(
                forecaster=forecaster,
                cv=cv,
                cogs_column=cogs_column,
                residual_target=residual_target,
            )
            results, preds = trainer.run_cv(df, return_predictions=True)
            all_results[model_type] = results
            all_preds[model_type] = preds

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

    # Compute weighted ensemble CV score from fold predictions.
    # Weights = inverse total MAE (lower MAE → higher weight).
    model_weights: dict[str, float] = {}
    for model_type in available:
        model_weights[model_type] = 1.0 / max(scores[model_type], 1.0)
    weight_sum = sum(model_weights.values())
    normalized_weights = [model_weights[m] / weight_sum for m in available]

    ensemble_results: dict[str, list[dict[str, float]]] = {"revenue": [], "cogs": []}
    for fold_idx in range(n_folds):
        fold_frames = []
        for model_type in available:
            fold_frames.append(all_preds[model_type][fold_idx])
        # Align on date and weighted average
        merged = fold_frames[0][["date", "revenue_pred", "cogs_pred"]].copy()
        merged = merged.rename(columns={"revenue_pred": "revenue_0", "cogs_pred": "cogs_0"})
        for i, frame in enumerate(fold_frames[1:], start=1):
            merged = merged.merge(frame[["date", "revenue_pred", "cogs_pred"]], on="date")
            merged = merged.rename(
                columns={"revenue_pred": f"revenue_{i}", "cogs_pred": f"cogs_{i}"}
            )
        rev_cols = [c for c in merged.columns if c.startswith("revenue_")]
        cogs_cols = [c for c in merged.columns if c.startswith("cogs_")]

        w = np.array(normalized_weights)
        merged["revenue_pred"] = np.average(merged[rev_cols].to_numpy(), axis=1, weights=w)
        merged["cogs_pred"] = np.average(merged[cogs_cols].to_numpy(), axis=1, weights=w)

        # Merge with actuals from the first model's fold predictions
        actual = fold_frames[0][["date"]].copy()
        actual = actual.merge(
            df[["sales_date", "revenue", "cogs"]].rename(columns={"sales_date": "date"}),
            on="date",
        )
        merged = merged.merge(actual, on="date")

        for target in ("revenue", "cogs"):
            y_true = merged[f"{target}"].to_numpy()
            y_pred = merged[f"{target}_pred"].to_numpy()
            mae = float(np.mean(np.abs(y_true - y_pred)))
            rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
            r2 = (
                float(1 - np.sum((y_true - y_pred) ** 2) / np.sum((y_true - np.mean(y_true)) ** 2))
                if np.var(y_true) > 0
                else 0.0
            )
            ensemble_results[target].append(
                {"fold": fold_idx + 1, "mae": mae, "rmse": rmse, "r2": r2}
            )

    avg_ens_rev = sum(r["mae"] for r in ensemble_results["revenue"]) / len(
        ensemble_results["revenue"]
    )
    avg_ens_cogs = sum(r["mae"] for r in ensemble_results["cogs"]) / len(ensemble_results["cogs"])
    scores["ensemble"] = avg_ens_rev + avg_ens_cogs
    all_results["ensemble"] = ensemble_results

    winner = min(scores, key=scores.get)
    return winner, all_results, all_preds, normalized_weights


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
    config = load_modeling_config(options.config_path)
    revenue_column, cogs_column, residual_target = resolve_targets(config)

    console.print(
        f"Comparing [bold]{len(list_forecasters())}[/bold] model types + weighted ensemble on "
        f"[bold]{len(df)}[/bold] rows (COGS target: {cogs_column}, residual: {residual_target}) …"
    )

    winner, all_results, _all_preds, ensemble_weights = _run_comparison(
        df, config, options.n_folds, options.horizon_days, cogs_column, residual_target
    )
    _print_summary(all_results, winner)

    console.print("\nTraining final models on full history …")
    available = list_forecasters()
    for model_type in available:
        model_dir = options.model_dir / model_type
        if model_dir.exists() and not options.force:
            console.print(f"  [dim]{model_type}: already exists at {model_dir}, skipping.[/dim]")
            continue
        forecaster = build_forecaster(model_type, config)
        trainer = Trainer(
            forecaster=forecaster,
            cv=ExpandingWindowCV(),
            cogs_column=cogs_column,
            residual_target=residual_target,
        )
        forecaster_fitted, feature_cols = trainer.train_final(df)
        Trainer.save_artifacts(
            model_dir=model_dir,
            forecaster=forecaster_fitted,
            feature_cols=feature_cols,
            model_type=model_type,
            cv_results=all_results.get(model_type),
            cogs_column=cogs_column,
            residual_target=residual_target,
        )
        console.print(f"  [green]{model_type}[/green] saved to {model_dir}")

    # Generate submission from the true winner
    if winner == "ensemble":
        console.print(
            f"\n[bold]Ensemble won CV — generating weighted ensemble submission "
            f"(weights: {[f'{w:.3f}' for w in ensemble_weights]}) …[/bold]"
        )
        members = []
        feature_cols = None
        cogs_is_ratio = False
        for model_type in available:
            model_path = options.model_dir / model_type
            forecaster, cols, _loaded_type, cogs_col, _residual = Trainer.load_artifacts(model_path)
            members.append(forecaster)
            if feature_cols is None:
                feature_cols = cols
                cogs_is_ratio = cogs_col == "cogs_ratio"
        ensemble = EnsembleForecaster(members=members, weights=list(ensemble_weights))
        scaffold = load_scaffold(options.warehouse)
        predictions = recursive_forecast(
            forecaster=ensemble,
            history=df,
            scaffold=scaffold,
            feature_cols=feature_cols,
            cogs_is_ratio=cogs_is_ratio,
            residual_target=residual_target,
        )
    else:
        console.print(f"\n[bold]{winner}[/bold] won CV — generating winner submission …")
        winner_dir = options.model_dir / winner
        winner_fitted, feature_cols, _model_type, winner_cogs_col, winner_residual = (
            Trainer.load_artifacts(winner_dir)
        )
        winner_cogs_is_ratio = winner_cogs_col == "cogs_ratio"
        scaffold = load_scaffold(options.warehouse)
        predictions = recursive_forecast(
            forecaster=winner_fitted,
            history=df,
            scaffold=scaffold,
            feature_cols=feature_cols,
            cogs_is_ratio=winner_cogs_is_ratio,
            residual_target=winner_residual,
        )

    expected = submission_columns()
    submission = predictions.rename(
        columns={"date": expected[0], "revenue": expected[1], "cogs": expected[2]}
    )
    submission = submission[expected]

    options.output_path.parent.mkdir(parents=True, exist_ok=True)
    submission.to_csv(options.output_path, index=False)
    console.print(f"Submission written to [bold]{options.output_path}[/bold]")
