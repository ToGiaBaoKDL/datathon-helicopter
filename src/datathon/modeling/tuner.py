"""Optuna-based hyperparameter tuning for forecasters."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import optuna
import pandas as pd

from datathon.modeling.cv import build_cv
from datathon.modeling.factory import build_forecaster
from datathon.modeling.metrics import fold_metrics
from datathon.modeling.recursive import (
    _PYTHON_ONLY_FEATURES,
    _STATIC_FEATURES,
    _backfill_historical_features,
    _ensure_columns,
    direct_forecast,
    feature_columns,
    recursive_forecast,
)
from datathon.tracking import MlflowTracker, OptunaMLflowCallback
from datathon.utils.config import load_modeling_config, resolve_targets

optuna.logging.set_verbosity(optuna.logging.WARNING)


def _suggest_lightgbm(trial: optuna.Trial) -> dict[str, Any]:
    """Suggest LightGBM hyperparameters (tree structure + regularisation only)."""
    return {
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
        "num_leaves": trial.suggest_int("num_leaves", 15, 150, step=5),
        "max_depth": trial.suggest_int("max_depth", 3, 12),
        "min_child_samples": trial.suggest_int("min_child_samples", 5, 100),
        "subsample": trial.suggest_float("subsample", 0.5, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
        "reg_alpha": trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
        "reg_lambda": trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
    }


def _suggest_xgboost(trial: optuna.Trial) -> dict[str, Any]:
    """Suggest XGBoost hyperparameters."""
    return {
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
        "max_depth": trial.suggest_int("max_depth", 3, 12),
        "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
        "gamma": trial.suggest_float("gamma", 1e-8, 1.0, log=True),
        "subsample": trial.suggest_float("subsample", 0.5, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
        "reg_alpha": trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
        "reg_lambda": trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
    }


def _suggest_catboost(
    trial: optuna.Trial, base_config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Suggest CatBoost hyperparameters.

    ``bagging_temperature`` is only suggested when the base config uses
    ``bootstrap_type="Bayesian"`` (the CatBoost default).  For other
    bootstrap types (e.g. "Bernoulli", "MVS") the parameter is omitted
    because CatBoost rejects it.
    """
    cfg: dict[str, Any] = {
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
        "depth": trial.suggest_int("depth", 4, 10),
        "l2_leaf_reg": trial.suggest_float("l2_leaf_reg", 1e-8, 10.0, log=True),
        "random_strength": trial.suggest_float("random_strength", 1e-8, 10.0, log=True),
    }
    cat_cfg = (base_config or {}).get("models", {}).get("catboost", {})
    bootstrap_type = cat_cfg.get("bootstrap_type", "Bayesian")
    if bootstrap_type == "Bayesian":
        cfg["bagging_temperature"] = trial.suggest_float("bagging_temperature", 0.0, 1.0)
    return cfg


def _inject_fixed_params(
    tuned_cfg: dict[str, Any],
    base_config: dict[str, Any],
    model_type: str,
) -> dict[str, Any]:
    """Merge tuned hyperparameters with fixed params from base config."""
    base_model = base_config.get("models", {}).get(model_type, {})
    cfg = dict(tuned_cfg)
    for key, val in base_model.items():
        if key not in cfg:
            cfg[key] = val
    return cfg


def _make_objective(
    df: pd.DataFrame,
    model_type: str,
    base_config: dict[str, Any],
    cogs_column: str,
    target_transform: str = "identity",
    n_folds: int = 2,
    horizon_days: int = 548,
    cv_type: str = "expanding",
    train_window_days: int = 1096,
    purge_days: int = 0,
    restart_horizon: int | None = None,
) -> callable:
    """Build an Optuna objective that minimises total MAE with per-fold pruning."""
    cogs_is_ratio = cogs_column == "cogs_ratio"
    if target_transform in ("residual", "log_residual"):
        revenue_column = "revenue_residual"
    elif target_transform == "log":
        revenue_column = "log_revenue"
    else:
        revenue_column = "revenue"

    _ensure_columns(df, _PYTHON_ONLY_FEATURES)
    _backfill_historical_features(df)
    cols = feature_columns(df)
    forecast_mode = base_config.get("forecast_mode", "recursive")
    if forecast_mode == "direct":
        cols = [c for c in cols if c in _STATIC_FEATURES]

    cv = build_cv(n_folds, horizon_days, cv_type, train_window_days, purge_days)

    def objective(trial: optuna.Trial) -> float:
        if model_type == "lightgbm":
            cfg = _suggest_lightgbm(trial)
        elif model_type == "xgboost":
            cfg = _suggest_xgboost(trial)
        elif model_type == "catboost":
            cfg = _suggest_catboost(trial, base_config)
        else:
            raise ValueError(f"Unsupported model_type for tuning: {model_type}")

        cfg = _inject_fixed_params(cfg, base_config, model_type)
        forecaster = build_forecaster(
            model_type,
            {
                "models": {model_type: cfg},
                "sequential_cogs": base_config.get("sequential_cogs", False),
            },
        )

        total_maes: list[float] = []
        best_rev_iter: int | None = None
        best_cogs_iter: int | None = None

        for fold, train_idx, val_idx in cv.split(df):
            train_df = df.iloc[train_idx]
            val_df = df.iloc[val_idx]

            max_days = (train_df["sales_date"].max() - train_df["sales_date"]).dt.days
            sw = np.exp(-0.001 * max_days.to_numpy())
            sw = sw / sw.sum() * len(sw)

            forecaster.fit(
                train_df[cols],
                train_df[revenue_column],
                train_df[cogs_column],
                eval_set=(val_df[cols], val_df[revenue_column], val_df[cogs_column]),
                sample_weight=sw,
            )

            rev_iter, cogs_iter = forecaster.best_iterations()
            if rev_iter is not None:
                best_rev_iter = rev_iter if best_rev_iter is None else max(best_rev_iter, rev_iter)
            if cogs_iter is not None:
                best_cogs_iter = (
                    cogs_iter if best_cogs_iter is None else max(best_cogs_iter, cogs_iter)
                )

            # Pass full validation frame (renamed) so known-in-advance features
            # such as promo intensity are available for each validation day.
            val_scaffold = val_df.rename(columns={"sales_date": "date"})
            if forecast_mode == "direct":
                pred = direct_forecast(
                    forecaster,
                    train_df,
                    val_scaffold,
                    cols,
                    cogs_is_ratio=cogs_is_ratio,
                    target_transform=target_transform,
                )
            else:
                pred = recursive_forecast(
                    forecaster,
                    train_df,
                    val_scaffold,
                    cols,
                    cogs_is_ratio=cogs_is_ratio,
                    target_transform=target_transform,
                    restart_horizon=restart_horizon,
                )

            merged = (
                val_df[["sales_date", "revenue", "cogs"]]
                .rename(columns={"sales_date": "date"})
                .merge(pred, on="date", suffixes=("_actual", "_pred"))
            )

            rev_m = fold_metrics(
                merged["revenue_actual"].to_numpy(), merged["revenue_pred"].to_numpy()
            )
            cogs_m = fold_metrics(merged["cogs_actual"].to_numpy(), merged["cogs_pred"].to_numpy())
            fold_total_mae = rev_m["mae"] + cogs_m["mae"]
            total_maes.append(fold_total_mae)

            trial.set_user_attr("rev_mae", rev_m["mae"])
            trial.set_user_attr("cogs_mae", cogs_m["mae"])
            trial.set_user_attr("rev_rmse", rev_m["rmse"])
            trial.set_user_attr("cogs_rmse", cogs_m["rmse"])
            trial.set_user_attr("rev_r2", rev_m["r2"])
            trial.set_user_attr("cogs_r2", cogs_m["r2"])
            trial.set_user_attr("fold_total_rmse", rev_m["rmse"] + cogs_m["rmse"])

            cumulative_mae = float(np.mean(total_maes))
            trial.report(cumulative_mae, step=fold)

            if trial.should_prune():
                raise optuna.TrialPruned()

        if best_rev_iter is not None:
            trial.set_user_attr("best_iteration_rev", best_rev_iter)
        if best_cogs_iter is not None:
            trial.set_user_attr("best_iteration_cogs", best_cogs_iter)

        return float(np.mean(total_maes))

    return objective


def run_study(
    df: pd.DataFrame,
    model_type: str,
    n_trials: int = 50,
    timeout: int | None = None,
    n_folds: int = 2,
    horizon_days: int = 548,
    cv_type: str = "expanding",
    train_window_days: int = 1096,
    purge_days: int = 0,
    study_name: str | None = None,
    storage: str | None = None,
    seed: int = 42,
    config_path: Path | None = None,
) -> tuple[dict[str, Any], float, float, float, float]:
    """Run an Optuna study and return best params + best total MAE."""
    config = load_modeling_config(config_path)
    revenue_column, cogs_column, target_transform, cogs_is_ratio = resolve_targets(config)

    tracker = MlflowTracker(run_name=f"tune_{model_type}")
    with tracker:
        if tracker.enabled:
            tracker.log_param("model_type", model_type)
            tracker.log_param("n_trials", n_trials)
            tracker.log_param("n_folds", n_folds)
            tracker.log_param("horizon_days", horizon_days)
            tracker.log_param("cv_type", cv_type)
            tracker.log_param("purge_days", purge_days)
            tracker.log_param("seed", seed)
            tracker.log_config(config)

        study_name = study_name or f"datathon_{model_type}"
        study = optuna.create_study(
            study_name=study_name,
            storage=storage,
            direction="minimize",
            sampler=optuna.samplers.TPESampler(seed=seed),
            pruner=optuna.pruners.MedianPruner(n_startup_trials=5, n_warmup_steps=1),
            load_if_exists=True,
        )

        restart_horizon = config.get("restart_horizon")
        objective = _make_objective(
            df,
            model_type,
            config,
            cogs_column,
            target_transform,
            n_folds,
            horizon_days,
            cv_type,
            train_window_days,
            purge_days,
            restart_horizon=restart_horizon,
        )
        callbacks: list = []
        if tracker.enabled:
            callbacks.append(OptunaMLflowCallback(tracker))

        study.optimize(
            objective,
            n_trials=n_trials,
            timeout=timeout,
            show_progress_bar=True,
            callbacks=callbacks,
        )

        best_trial = study.best_trial
        best_params = dict(best_trial.params)
        best_value = float(best_trial.value)

        rev_iter = best_trial.user_attrs.get("best_iteration_rev")
        cogs_iter = best_trial.user_attrs.get("best_iteration_cogs")

        best_iter = None
        if rev_iter is not None:
            best_iter = int(rev_iter)
        if cogs_iter is not None:
            best_iter = int(cogs_iter) if best_iter is None else max(best_iter, int(cogs_iter))
        if best_iter is not None:
            key = "iterations" if model_type == "catboost" else "n_estimators"
            best_params[key] = best_iter

        best_params = _inject_fixed_params(best_params, config, model_type)

        if tracker.enabled:
            tracker.log_metric("best_total_mae", best_value)
            tracker.log_metric("best_rev_mae", float(best_trial.user_attrs.get("rev_mae", 0)))
            tracker.log_metric("best_cogs_mae", float(best_trial.user_attrs.get("cogs_mae", 0)))
            tracker.log_metric("best_rev_rmse", float(best_trial.user_attrs.get("rev_rmse", 0)))
            tracker.log_metric("best_cogs_rmse", float(best_trial.user_attrs.get("cogs_rmse", 0)))
            tracker.log_metric("best_rev_r2", float(best_trial.user_attrs.get("rev_r2", 0)))
            tracker.log_metric("best_cogs_r2", float(best_trial.user_attrs.get("cogs_r2", 0)))
            tracker.log_params({f"best_{k}": v for k, v in best_params.items()})
            tracker.log_dict(best_params, "best_params.json")
            tracker.set_tag("model_type", model_type)
            tracker.set_tag("status", "tuned")
            tracker.set_tag("optuna_study", study_name)

        best_rmse = float(best_trial.user_attrs.get("fold_total_rmse", 0))
        best_r2_rev = float(best_trial.user_attrs.get("rev_r2", 0))
        best_r2_cogs = float(best_trial.user_attrs.get("cogs_r2", 0))

        return best_params, best_value, best_rmse, best_r2_rev, best_r2_cogs
