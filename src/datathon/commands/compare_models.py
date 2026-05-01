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
from datathon.modeling.recursive import direct_forecast, recursive_forecast
from datathon.modeling.trainer import Trainer
from datathon.tracking import MlflowTracker
from datathon.utils.competition import submission_columns
from datathon.utils.config import load_modeling_config, merge_model_config, resolve_targets
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
    restart_horizon: int | None = None,
    forecast_mode: str = "recursive",
) -> tuple[
    str,
    dict,
    dict[str, list[pd.DataFrame]],
    list[float],
    dict[str, list[tuple[int | None, int | None]]],
    object | None,
    object | None,
]:
    """Run CV for all models, compute weighted ensemble CV."""
    cv = build_cv(n_folds, horizon_days, cv_type, train_window_days, purge_days)
    all_results: dict[str, dict[str, list[dict[str, float]]]] = {}
    all_preds: dict[str, list[pd.DataFrame]] = {}
    all_best_iters: dict[str, list[tuple[int | None, int | None]]] = {}
    scores: dict[str, float] = {}

    available = list_forecasters()
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for model_type in available:
            task = progress.add_task(f"Evaluating {model_type} …", total=None)
            model_config = merge_model_config(config, model_type)
            forecaster = build_forecaster(model_type, model_config)
            trainer = Trainer(
                forecaster=forecaster,
                cv=cv,
                cogs_column=cogs_column,
                target_transform=target_transform,
                forecast_mode=forecast_mode,
            )
            results, preds = trainer.run_cv(
                df, return_predictions=True, sample_weight=True, restart_horizon=restart_horizon
            )
            all_results[model_type] = results
            all_preds[model_type] = preds
            all_best_iters[model_type] = list(trainer._last_cv_best_iters)

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
    actuals_cols = ["sales_date", "revenue", "cogs"]
    if target_transform in ("residual", "log_residual"):
        actuals_cols.extend(
            ["revenue_residual", "cogs_residual", "revenue_baseline", "cogs_baseline"]
        )
    if target_transform == "log_residual":
        actuals_cols.extend(["log_revenue_baseline", "log_cogs_baseline"])
    if target_transform == "log":
        actuals_cols.extend(["log_revenue", "log_cogs"])
    actuals_df = df[actuals_cols].rename(columns={"sales_date": "date"})
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

    # ------------------------------------------------------------------
    # Stacking meta-learner (optional)
    # ------------------------------------------------------------------
    meta_rev = None
    meta_cogs = None
    if config.get("stacking", False):
        # Collect OOF predictions across all folds
        oof_rev = {m: [] for m in available}
        oof_cogs = {m: [] for m in available}
        oof_y_rev = []
        oof_y_cogs = []
        # Collect raw actuals for MAE computation (same scale as other models)
        oof_raw_rev = []
        oof_raw_cogs = []

        for fold_idx in range(cv.n_folds):
            fold_actuals = actuals_df.merge(all_preds[available[0]][fold_idx][["date"]], on="date")
            # Target for meta-learner = raw targets (same as ensemble)
            oof_y_rev.extend(fold_actuals["revenue"].to_numpy())
            oof_y_cogs.extend(fold_actuals["cogs"].to_numpy())
            # Raw actuals for final MAE (must match other models' scale)
            oof_raw_rev.extend(fold_actuals["revenue"].to_numpy())
            oof_raw_cogs.extend(fold_actuals["cogs"].to_numpy())
            for m in available:
                preds = all_preds[m][fold_idx]
                merged = fold_actuals.merge(preds, on="date")
                oof_rev[m].extend(merged["revenue_pred"].to_numpy())
                oof_cogs[m].extend(merged["cogs_pred"].to_numpy())

        # Use simple non-negative least squares (NNLS) to learn weights
        # that minimise MAE on raw predictions.  NNLS forces positive
        # weights so we don't get destructive interference.
        from scipy.optimize import nnls

        X_meta_rev = np.column_stack([oof_rev[m] for m in available])
        X_meta_cogs = np.column_stack([oof_cogs[m] for m in available])

        w_rev, _ = nnls(X_meta_rev, np.asarray(oof_y_rev, dtype=float))
        w_cogs, _ = nnls(X_meta_cogs, np.asarray(oof_y_cogs, dtype=float))
        # Normalise to sum=1
        w_rev = w_rev / w_rev.sum() if w_rev.sum() > 0 else np.ones(len(available)) / len(available)
        w_cogs = (
            w_cogs / w_cogs.sum() if w_cogs.sum() > 0 else np.ones(len(available)) / len(available)
        )

        # Store weights directly (pickle-friendly)
        meta_rev = w_rev
        meta_cogs = w_cogs

        # Compute stacked CV score on RAW scale (comparable with other models)
        stacked_rev_raw = np.average(X_meta_rev, axis=1, weights=meta_rev)
        stacked_cogs_raw = np.average(X_meta_cogs, axis=1, weights=meta_cogs)

        stacked_rev_mae = float(np.abs(np.asarray(oof_raw_rev) - stacked_rev_raw).mean())
        stacked_cogs_mae = float(np.abs(np.asarray(oof_raw_cogs) - stacked_cogs_raw).mean())
        scores["stacked"] = stacked_rev_mae + stacked_cogs_mae
        all_results["stacked"] = {
            "revenue": [{"fold": 1, "mae": stacked_rev_mae, "rmse": 0.0, "r2": 0.0}],
            "cogs": [{"fold": 1, "mae": stacked_cogs_mae, "rmse": 0.0, "r2": 0.0}],
        }
        console.print(
            f"[bold cyan]Stacked ensemble[/bold cyan] — "
            f"Rev MAE {stacked_rev_mae:,.0f} | COGS MAE {stacked_cogs_mae:,.0f} | "
            f"Total {stacked_rev_mae + stacked_cogs_mae:,.0f}"
        )
        console.print(f"  Meta weights (rev): {dict(zip(available, w_rev.tolist(), strict=True))}")

    winner = min(scores, key=scores.get)
    return winner, all_results, all_preds, ensemble_weights, all_best_iters, meta_rev, meta_cogs


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
    forecast_mode = config.get("forecast_mode", "recursive")

    cv_label = f"{options.cv_type}"
    if options.cv_type == "sliding":
        cv_label += f" (train={options.train_window_days}d)"
    if options.purge_days > 0:
        cv_label += f" [purge={options.purge_days}d]"

    console.print(
        f"Comparing [bold]{len(list_forecasters())}[/bold] model types + weighted ensemble on "
        f"[bold]{len(df)}[/bold] rows | COGS: {cogs_column} | transform: {target_transform} | "
        f"forecast_mode=[bold]{forecast_mode}[/bold] | "
        f"sequential_cogs=[bold]{config.get('sequential_cogs', False)}[/bold] | "
        f"restart_horizon=[bold]{config.get('restart_horizon', 'null')}[/bold] | "
        f"CV: {options.n_folds}-fold × {options.horizon_days}d ({cv_label}) …"
    )

    restart_horizon = config.get("restart_horizon")
    (
        winner,
        all_results,
        _all_preds,
        ensemble_weights,
        all_best_iters,
        meta_rev,
        meta_cogs,
    ) = _run_comparison(
        df,
        config,
        options.n_folds,
        options.horizon_days,
        options.cv_type,
        options.train_window_days,
        options.purge_days,
        cogs_column,
        target_transform,
        restart_horizon=restart_horizon,
        forecast_mode=forecast_mode,
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
            model_config = merge_model_config(config, model_type)
            forecaster = build_forecaster(model_type, model_config)
            cv = build_cv(n_folds=1, horizon_days=1, cv_type="expanding")
            trainer = Trainer(
                forecaster=forecaster,
                cv=cv,
                cogs_column=cogs_column,
                target_transform=target_transform,
                forecast_mode=forecast_mode,
            )
            if model_type in all_best_iters:
                trainer._last_cv_best_iters = list(all_best_iters[model_type])
            forecaster_fitted, feature_cols = trainer.train_final(df, sample_weight=True)

            spike_classifier = None
            if config.get("spike_classifier", False):
                from datathon.modeling.spike_classifier import SpikeClassifier

                spike_classifier = SpikeClassifier()
                spike_classifier.fit(df[feature_cols], df["revenue"])

            Trainer.save_artifacts(
                model_dir=model_dir,
                forecaster=forecaster_fitted,
                feature_cols=feature_cols,
                model_type=model_type,
                cv_results=all_results.get(model_type),
                cogs_column=cogs_column,
                target_transform=target_transform,
                sequential_cogs=model_config.get("sequential_cogs", False),
                restart_horizon=model_config.get("restart_horizon"),
                forecast_mode=forecast_mode,
                spike_classifier=spike_classifier,
            )
            console.print(f"  [green]{model_type}[/green] saved to {model_dir}")

            if tracker.enabled:
                tracker.log_model(model_dir, artifact_path=f"models/{model_type}")

        # Save stacked ensemble if stacking was trained
        if meta_rev is not None and meta_cogs is not None:
            from datathon.modeling.forecasters.stacking import StackingForecaster

            stack_dir = options.model_dir / "stacked"
            stack_dir.mkdir(parents=True, exist_ok=True)
            members = []
            for model_type in available:
                model_path = options.model_dir / model_type
                forecaster, _cols, _loaded_type, _cogs_col, _transform, _seq, _rh, _fm, _spk = (
                    Trainer.load_artifacts(model_path)
                )
                members.append(forecaster)
            stacked = StackingForecaster(members=members, meta_rev=meta_rev, meta_cogs=meta_cogs)
            stacked.save(stack_dir / "forecaster.pkl")
            # Load feature cols from first model
            _fc, feature_cols, _mt, _cc, _tt, _sc, _rh, _fm, _spk = Trainer.load_artifacts(
                options.model_dir / available[0]
            )
            Trainer.save_artifacts(
                model_dir=stack_dir,
                forecaster=stacked,
                feature_cols=feature_cols,
                model_type="stacked",
                cv_results=all_results.get("stacked"),
                cogs_column=cogs_column,
                target_transform=target_transform,
                sequential_cogs=False,
                restart_horizon=restart_horizon,
                forecast_mode=forecast_mode,
            )
            console.print(f"  [green]stacked[/green] saved to {stack_dir}")

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
        scaffold = load_scaffold(options.warehouse)
        if config.get("promo_features", False):
            from datathon.utils.data_loaders import _apply_promo_features_to_scaffold

            scaffold = _apply_promo_features_to_scaffold(scaffold, options.warehouse)

        def _make_predictions(forecaster, feature_cols, cogs_is_ratio, trans):
            if forecast_mode == "direct":
                return direct_forecast(
                    forecaster=forecaster,
                    history=df,
                    scaffold=scaffold,
                    feature_cols=feature_cols,
                    cogs_is_ratio=cogs_is_ratio,
                    target_transform=trans,
                )
            return recursive_forecast(
                forecaster=forecaster,
                history=df,
                scaffold=scaffold,
                feature_cols=feature_cols,
                cogs_is_ratio=cogs_is_ratio,
                target_transform=trans,
                restart_horizon=restart_horizon,
            )

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
                forecaster, cols, _loaded_type, cogs_col, _transform, _seq, _rh, _fm, _spk = (
                    Trainer.load_artifacts(model_path)
                )
                members.append(forecaster)
                if feature_cols is None:
                    feature_cols = cols
                    cogs_is_ratio = cogs_col == "cogs_ratio"
            ensemble = EnsembleForecaster(members=members, weights=list(ensemble_weights))
            predictions = _make_predictions(ensemble, feature_cols, cogs_is_ratio, target_transform)
        elif winner == "stacked":
            console.print(
                "\n[bold]Stacked ensemble won CV — generating stacked submission …[/bold]"
            )
            from datathon.modeling.forecasters.stacking import StackingForecaster

            stack_dir = options.model_dir / "stacked"
            (
                stacked_fitted,
                feature_cols,
                _mt,
                winner_cogs_col,
                winner_transform,
                _seq,
                _rh,
                _fm,
                _spk,
            ) = Trainer.load_artifacts(stack_dir)
            winner_cogs_is_ratio = winner_cogs_col == "cogs_ratio"
            predictions = _make_predictions(
                stacked_fitted, feature_cols, winner_cogs_is_ratio, winner_transform
            )
        else:
            console.print(f"\n[bold]{winner}[/bold] won CV — generating winner submission …")
            winner_dir = options.model_dir / winner
            (
                winner_fitted,
                feature_cols,
                _model_type,
                winner_cogs_col,
                winner_transform,
                _seq,
                _rh,
                _fm,
                winner_spike,
            ) = Trainer.load_artifacts(winner_dir)
            winner_cogs_is_ratio = winner_cogs_col == "cogs_ratio"
            predictions = _make_predictions(
                winner_fitted, feature_cols, winner_cogs_is_ratio, winner_transform
            )
            # Apply spike boost if the winner model has a spike classifier
            if winner_spike is not None:
                console.print("Applying spike boost …")
                from datathon.modeling.recursive import _prepare_future_frame

                future_frame = _prepare_future_frame(df, scaffold)
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
                    spike_prob = winner_spike.predict_proba(future_frame[static_cols])
                    old_revenue = predictions["revenue"].to_numpy().copy()
                    old_cogs = (
                        predictions["cogs"].to_numpy().copy()
                        if "cogs" in predictions.columns
                        else None
                    )
                    predictions["revenue"] = winner_spike.apply_boost(old_revenue, spike_prob)
                    if winner_cogs_is_ratio and old_cogs is not None:
                        ratio = np.divide(
                            old_cogs,
                            old_revenue,
                            out=np.zeros_like(old_cogs),
                            where=old_revenue != 0,
                        )
                        ratio = np.clip(ratio, 0.0, 2.0)
                        predictions["cogs"] = predictions["revenue"].to_numpy() * ratio
                    console.print(
                        f"  Spike boost applied (max boost: {winner_spike.max_boost:.2f})"
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
