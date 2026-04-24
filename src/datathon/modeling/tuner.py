"""Optuna-based hyperparameter tuning for forecasters."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import optuna
import pandas as pd

from datathon.modeling.cv import ExpandingWindowCV
from datathon.modeling.factory import build_forecaster
from datathon.modeling.recursive import feature_columns, recursive_forecast
from datathon.utils.config import load_modeling_config

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


def _suggest_catboost(trial: optuna.Trial) -> dict[str, Any]:
    """Suggest CatBoost hyperparameters."""
    return {
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
        "depth": trial.suggest_int("depth", 4, 10),
        "l2_leaf_reg": trial.suggest_float("l2_leaf_reg", 1e-8, 10.0, log=True),
        "random_strength": trial.suggest_float("random_strength", 1e-8, 10.0, log=True),
        "bagging_temperature": trial.suggest_float("bagging_temperature", 0.0, 1.0),
    }


def _inject_fixed_params(
    tuned_cfg: dict[str, Any],
    base_config: dict[str, Any],
    model_type: str,
) -> dict[str, Any]:
    """Merge tuned hyperparameters with fixed params from base config.

    Any key present in the base model config but *not* in the tuned config
    is treated as a fixed param and copied over.  This avoids duplicating
    boilerplate (``n_estimators``, ``n_jobs``, ``objective``, etc.) in the
    search space while ensuring the forecaster is fully specified.
    """
    base_model = base_config.get("models", {}).get(model_type, {})
    cfg = dict(tuned_cfg)
    for key, val in base_model.items():
        if key not in cfg:
            cfg[key] = val
    return cfg


def _make_stop_callback(patience: int = 10) -> callable:
    """Build an Optuna callback that stops the study after *patience*
    consecutive completed trials without improvement."""

    def callback(study: optuna.Study, trial: optuna.trial.FrozenTrial) -> None:
        if len(study.trials) < patience + 1:
            return
        complete = [t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE]
        if len(complete) <= patience:
            return
        recent = complete[-patience:]
        best = study.best_value
        if all(t.value >= best for t in recent):
            print(
                f"[Optuna] No improvement for {patience} consecutive trials. "
                f"Stopping study early (best value: {best:,.0f})."
            )
            study.stop()

    return callback


def _make_objective(
    df: pd.DataFrame,
    model_type: str,
    base_config: dict[str, Any],
    cogs_column: str,
    n_folds: int = 2,
    horizon_days: int = 548,
) -> callable:
    """Build an Optuna objective that minimises total MAE with per-fold pruning."""
    cogs_is_ratio = cogs_column == "cogs_ratio"

    def objective(trial: optuna.Trial) -> float:
        if model_type == "lightgbm":
            cfg = _suggest_lightgbm(trial)
        elif model_type == "xgboost":
            cfg = _suggest_xgboost(trial)
        elif model_type == "catboost":
            cfg = _suggest_catboost(trial)
        else:
            raise ValueError(f"Unsupported model_type for tuning: {model_type}")

        cfg = _inject_fixed_params(cfg, base_config, model_type)
        forecaster = build_forecaster(model_type, {"models": {model_type: cfg}})
        cv = ExpandingWindowCV(n_folds=n_folds, horizon_days=horizon_days)
        cols = feature_columns(df)

        total_maes: list[float] = []
        for fold, train_idx, val_idx in cv.split(df):
            train_df = df.iloc[train_idx]
            val_df = df.iloc[val_idx]

            forecaster.fit(
                train_df[cols],
                train_df["revenue"],
                train_df[cogs_column],
                eval_set=(val_df[cols], val_df["revenue"], val_df[cogs_column]),
            )

            rev_iter, cogs_iter = forecaster.best_iterations()
            if rev_iter is not None:
                trial.set_user_attr("best_iteration_rev", rev_iter)
            if cogs_iter is not None:
                trial.set_user_attr("best_iteration_cogs", cogs_iter)

            pred = recursive_forecast(
                forecaster,
                train_df,
                val_df[["sales_date"]].rename(columns={"sales_date": "date"}),
                cols,
                cogs_is_ratio=cogs_is_ratio,
            )

            merged = (
                val_df[["sales_date", "revenue", "cogs"]]
                .rename(columns={"sales_date": "date"})
                .merge(pred, on="date", suffixes=("_actual", "_pred"))
            )

            rev_mae = float(
                np.mean(
                    np.abs(merged["revenue_actual"].to_numpy() - merged["revenue_pred"].to_numpy())
                )
            )
            cogs_mae = float(
                np.mean(np.abs(merged["cogs_actual"].to_numpy() - merged["cogs_pred"].to_numpy()))
            )
            fold_total = rev_mae + cogs_mae
            total_maes.append(fold_total)

            # Report intermediate result for pruning.
            cumulative_mae = float(np.mean(total_maes))
            trial.report(cumulative_mae, step=fold)

            if trial.should_prune():
                raise optuna.TrialPruned()

        return float(np.mean(total_maes))

    return objective


def run_study(
    df: pd.DataFrame,
    model_type: str,
    n_trials: int = 30,
    timeout: int | None = None,
    n_folds: int = 2,
    horizon_days: int = 548,
    study_name: str | None = None,
    storage: str | None = None,
    seed: int = 42,
    patience: int = 10,
    config_path: Path | None = None,
) -> tuple[dict[str, Any], float]:
    """Run an Optuna study and return best params + best total MAE.

    Parameters
    ----------
    df:
        Historical data (already loaded from warehouse).
    model_type:
        One of ``lightgbm``, ``xgboost``, ``catboost``.
    n_trials:
        Number of Optuna trials (hard upper bound).
    timeout:
        Max seconds for the study (``None`` = unlimited).
    n_folds, horizon_days:
        CV parameters for the objective.
    study_name:
        Name for the Optuna study (defaults to ``datathon_<model_type>``).
    storage:
        Optuna storage URL (``None`` = in-memory).
    seed:
        Random seed for reproducibility.
    patience:
        Stop the study early if no improvement for this many consecutive
        completed trials.
    config_path:
        Optional path to a delta config overlay (e.g. a previous tuning
        result to refine from).

    Returns
    -------
    (best_params, best_total_mae)
    """
    config = load_modeling_config(config_path)
    cogs_target = config.get("cogs_target", "absolute")
    cogs_column = "cogs_ratio" if cogs_target == "ratio" else "cogs"

    study_name = study_name or f"datathon_{model_type}"
    study = optuna.create_study(
        study_name=study_name,
        storage=storage,
        direction="minimize",
        sampler=optuna.samplers.TPESampler(seed=seed),
        pruner=optuna.pruners.MedianPruner(n_startup_trials=5, n_warmup_steps=1),
        load_if_exists=True,
    )

    objective = _make_objective(df, model_type, config, cogs_column, n_folds, horizon_days)
    stop_callback = _make_stop_callback(patience=patience)
    study.optimize(
        objective,
        n_trials=n_trials,
        timeout=timeout,
        show_progress_bar=True,
        callbacks=[stop_callback],
    )

    best_trial = study.best_trial
    best_params = dict(best_trial.params)
    best_value = float(best_trial.value)

    rev_iter = best_trial.user_attrs.get("best_iteration_rev")
    cogs_iter = best_trial.user_attrs.get("best_iteration_cogs")

    # Use the more conservative (larger) ceiling so neither model is cut short.
    best_iter = None
    if rev_iter is not None:
        best_iter = int(rev_iter)
    if cogs_iter is not None:
        best_iter = int(cogs_iter) if best_iter is None else max(best_iter, int(cogs_iter))
    if best_iter is not None:
        key = "iterations" if model_type == "catboost" else "n_estimators"
        best_params[key] = best_iter

    # Merge fixed params so the returned config is self-contained.
    best_params = _inject_fixed_params(best_params, config, model_type)
    return best_params, best_value
