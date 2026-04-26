"""CLI command to compare all registered forecasters and pick the best one."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from datathon.commands.common import CommandError, ensure_no_unknown_args, take_option
from datathon.modeling.cv import build_cv
from datathon.modeling.factory import build_forecaster
from datathon.modeling.forecasters import list_forecasters
from datathon.modeling.forecasters.ensemble import EnsembleForecaster
from datathon.modeling.metrics import fold_metrics
from datathon.modeling.recursive import recursive_forecast
from datathon.modeling.trainer import Trainer
from datathon.tracking import MlflowTracker
from datathon.utils.competition import submission_columns
from datathon.utils.config import load_modeling_config, resolve_targets
from datathon.utils.console import console
from datathon.utils.data_loaders import load_scaffold, load_training_data
from datathon.utils.help_texts import compare_help
from datathon.utils.paths import models_dir, submissions_dir, warehouse_path


@dataclass(frozen=True)
class CompareOptions:
    warehouse: Path
    n_folds: int
    horizon_days: int
    cv_type: str
    train_window_days: int
    purge_days: int
    model_dir: Path
    output_path: Path
    config_path: Path | None
    force: bool


def parse_args(raw_args: list[str]) -> CompareOptions:
    args = list(raw_args)
    warehouse = Path(take_option(args, "--warehouse", default=str(warehouse_path())))
    n_folds = int(take_option(args, "--n-folds", default="2"))
    horizon_days = int(take_option(args, "--horizon-days", default="548"))
    cv_type = take_option(args, "--cv-type", default="sliding")
    train_window_days = int(take_option(args, "--train-window-days", default="1096"))
    purge_days = int(take_option(args, "--purge-days", default="7"))
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
    if cv_type not in ("expanding", "sliding"):
        raise CommandError("--cv-type must be 'expanding' or 'sliding'.")
    return CompareOptions(
        warehouse=warehouse,
        n_folds=n_folds,
        horizon_days=horizon_days,
        cv_type=cv_type,
        train_window_days=train_window_days,
        purge_days=purge_days,
        model_dir=model_dir,
        output_path=output_path,
        config_path=config_path,
        force=force,
    )


def print_help() -> None:
    console.print("[bold]compare-models[/bold]")
    console.print(compare_help())


def _run_comparison(
    df: pd.DataFrame,
    config: dict[str, Any],
    n_folds: int,
    horizon_days: int,
    cv_type: str,
    train_window_days: int,
    purge_days: int,
    cogs_column: str = "cogs",
    target_transform: str = "identity",
) -> tuple[str, dict, dict[str, list[pd.DataFrame]], list[float]]:
    """Run CV for all models, compute weighted ensemble CV."""
    cv = build_cv(n_folds, horizon_days, cv_type, train_window_days, purge_days)
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
                target_transform=target_transform,
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

    ensemble_results: dict[str, list[dict[str, float]]] = {"revenue": [], "cogs": []}
    actuals_df = df[["sales_date", "revenue", "cogs"]].rename(columns={"sales_date": "date"})
    fold_weights_all: list[list[float]] = []

    for fold_idx in range(cv.n_folds):
        fold_preds_by_model: dict[str, pd.DataFrame] = {
            m: all_preds[m][fold_idx] for m in available
        }
        ref_dates = fold_preds_by_model[available[0]]["date"]

        wide_rev = pd.DataFrame({"date": ref_dates})
        wide_cogs = pd.DataFrame({"date": ref_dates})
        for m in available:
            frm = fold_preds_by_model[m]
            wide_rev = wide_rev.merge(frm[["date", "revenue_pred"]], on="date").rename(
                columns={"revenue_pred": m}
            )
            wide_cogs = wide_cogs.merge(frm[["date", "cogs_pred"]], on="date").rename(
                columns={"cogs_pred": m}
            )

        fold_maes = {}
        for m in available:
            merged_fold = fold_preds_by_model[m].merge(actuals_df, on="date")
            rev_mae = float(np.abs(merged_fold["revenue"] - merged_fold["revenue_pred"]).mean())
            cogs_mae = float(np.abs(merged_fold["cogs"] - merged_fold["cogs_pred"]).mean())
            fold_maes[m] = rev_mae + cogs_mae

        w_arr = np.array([1.0 / max(fold_maes[m], 1.0) for m in available])
        fold_weights = (w_arr / w_arr.sum()).tolist()
        fold_weights_all.append(fold_weights)

        wide_rev["revenue_pred"] = np.average(
            wide_rev[list(available)].to_numpy(), axis=1, weights=fold_weights
        )
        wide_cogs["cogs_pred"] = np.average(
            wide_cogs[list(available)].to_numpy(), axis=1, weights=fold_weights
        )

        ens = (
            wide_rev[["date", "revenue_pred"]]
            .merge(wide_cogs[["date", "cogs_pred"]], on="date")
            .merge(actuals_df, on="date")
        )

        for target in ("revenue", "cogs"):
            y_true = ens[target].to_numpy()
            y_pred = ens[f"{target}_pred"].to_numpy()
            m = fold_metrics(y_true, y_pred)
            ensemble_results[target].append(
                {"fold": fold_idx + 1, "mae": m["mae"], "rmse": m["rmse"], "r2": m["r2"]}
            )

    avg_ens_rev = sum(r["mae"] for r in ensemble_results["revenue"]) / len(
        ensemble_results["revenue"]
    )
    avg_ens_cogs = sum(r["mae"] for r in ensemble_results["cogs"]) / len(ensemble_results["cogs"])
    scores["ensemble"] = avg_ens_rev + avg_ens_cogs
    all_results["ensemble"] = ensemble_results

    n_models = len(available)
    averaged_weights = [
        float(np.mean([fold_weights_all[f][i] for f in range(cv.n_folds)])) for i in range(n_models)
    ]
    w_sum = sum(averaged_weights)
    ensemble_weights = [w / w_sum for w in averaged_weights]

    winner = min(scores, key=scores.get)
    return winner, all_results, all_preds, ensemble_weights


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
    config = load_modeling_config(options.config_path)
    df = load_training_data(config, options.warehouse)
    _, cogs_column, target_transform, cogs_is_ratio = resolve_targets(config)

    cv_label = f"{options.cv_type}"
    if options.cv_type == "sliding":
        cv_label += f" (train={options.train_window_days}d)"
    if options.purge_days > 0:
        cv_label += f" [purge={options.purge_days}d]"

    console.print(
        f"Comparing [bold]{len(list_forecasters())}[/bold] model types + weighted ensemble on "
        f"[bold]{len(df)}[/bold] rows | COGS: {cogs_column} | transform: {target_transform} | "
        f"CV: {options.n_folds}-fold × {options.horizon_days}d ({cv_label}) …"
    )

    winner, all_results, _all_preds, ensemble_weights = _run_comparison(
        df,
        config,
        options.n_folds,
        options.horizon_days,
        options.cv_type,
        options.train_window_days,
        options.purge_days,
        cogs_column,
        target_transform,
    )
    _print_summary(all_results, winner)

    tracker = MlflowTracker(run_name="compare_models")
    with tracker:
        if tracker.enabled:
            tracker.log_param("n_folds", options.n_folds)
            tracker.log_param("horizon_days", options.horizon_days)
            tracker.log_param("cv_type", options.cv_type)
            tracker.log_param("purge_days", options.purge_days)
            tracker.log_config(config)

        console.print("\nTraining final models on full history …")
        available = list_forecasters()
        for model_type in available:
            model_dir = options.model_dir / model_type
            if model_dir.exists() and not options.force:
                console.print(
                    f"  [dim]{model_type}: already exists at {model_dir}, skipping.[/dim]"
                )
                continue
            forecaster = build_forecaster(model_type, config)
            cv = build_cv(n_folds=1, horizon_days=1, cv_type="expanding")
            trainer = Trainer(
                forecaster=forecaster,
                cv=cv,
                cogs_column=cogs_column,
                target_transform=target_transform,
            )
            forecaster_fitted, feature_cols = trainer.train_final(df)
            Trainer.save_artifacts(
                model_dir=model_dir,
                forecaster=forecaster_fitted,
                feature_cols=feature_cols,
                model_type=model_type,
                cv_results=all_results.get(model_type),
                cogs_column=cogs_column,
                target_transform=target_transform,
            )
            console.print(f"  [green]{model_type}[/green] saved to {model_dir}")

            if tracker.enabled:
                tracker.log_model(model_dir, artifact_path=f"models/{model_type}")

        if tracker.enabled:
            for model_type, results in all_results.items():
                avg_rev = sum(r["mae"] for r in results["revenue"]) / len(results["revenue"])
                avg_cogs = sum(r["mae"] for r in results["cogs"]) / len(results["cogs"])
                tracker.log_metric(f"{model_type}_rev_mae", avg_rev)
                tracker.log_metric(f"{model_type}_cogs_mae", avg_cogs)
                tracker.log_metric(f"{model_type}_total_mae", avg_rev + avg_cogs)
            tracker.log_dict(
                {m: float(w) for m, w in zip(available, ensemble_weights, strict=True)},
                "ensemble_weights.json",
            )
            tracker.set_tag("winner", winner)
            tracker.set_tag("status", "compared")

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
                forecaster, cols, _loaded_type, cogs_col, _transform = Trainer.load_artifacts(
                    model_path
                )
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
                target_transform=target_transform,
            )
        else:
            console.print(f"\n[bold]{winner}[/bold] won CV — generating winner submission …")
            winner_dir = options.model_dir / winner
            winner_fitted, feature_cols, _model_type, winner_cogs_col, winner_transform = (
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
                target_transform=winner_transform,
            )

        expected = submission_columns()
        submission = predictions.rename(
            columns={"date": expected[0], "revenue": expected[1], "cogs": expected[2]}
        )
        submission = submission[expected]

        options.output_path.parent.mkdir(parents=True, exist_ok=True)
        submission.to_csv(options.output_path, index=False)
        console.print(f"Submission written to [bold]{options.output_path}[/bold]")

        if tracker.enabled:
            tracker.log_artifact(options.output_path)
            tracker.set_tag("status", "submitted")
