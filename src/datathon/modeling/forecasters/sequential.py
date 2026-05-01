"""Sequential forecaster: revenue first, then COGS conditioned on predicted revenue."""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Self

import numpy as np
import pandas as pd

from datathon.modeling.forecasters.base import BaseForecaster


class SequentialForecaster(BaseForecaster):
    """Trains a dedicated revenue model, then feeds in-sample revenue predictions
    into the COGS model as an extra feature.

    This captures the extremely strong revenue-to-COGS relationship
    (corr ≈ 0.98) rather than wasting model capacity by predicting COGS
    independently.
    """

    PRED_REV_COL = "predicted_revenue"

    def __init__(self, model_type: str, **model_cfg) -> None:
        self.model_type = model_type
        self._model_cfg = dict(model_cfg)
        self._early_stopping_rounds = self._model_cfg.pop("early_stopping_rounds", 50)
        self.model_rev = None
        self.model_cogs = None

    # ------------------------------------------------------------------ #
    # Internal helpers – build single-target estimators
    # ------------------------------------------------------------------ #

    def _build_estimator(self) -> object:
        cfg = dict(self._model_cfg)
        if self.model_type == "lightgbm":
            import lightgbm as lgb

            if "random_state" not in cfg:
                cfg["random_state"] = 42
            return lgb.LGBMRegressor(**cfg)

        if self.model_type == "xgboost":
            import xgboost as xgb

            if "random_state" not in cfg:
                cfg["random_state"] = 42
            return xgb.XGBRegressor(**cfg)

        if self.model_type == "catboost":
            import catboost as cb

            if "random_seed" not in cfg and "random_state" not in cfg:
                cfg["random_seed"] = 42
            return cb.CatBoostRegressor(**cfg)

        raise ValueError(f"Unsupported model_type for SequentialForecaster: {self.model_type}")

    def _apply_early_stopping(self, estimator, es_rounds: int) -> None:
        """Attach early-stopping callbacks via ``set_params`` when needed.

        XGBoost 3.x requires callbacks on the estimator (not in ``fit()``);
        LightGBM and CatBoost accept them in ``fit()``.
        """
        if self.model_type == "xgboost":
            import xgboost as xgb

            estimator.set_params(callbacks=[xgb.callback.EarlyStopping(rounds=es_rounds)])

    @staticmethod
    def _fit_kwargs(model_type: str, es_rounds: int, X_val, y_val):
        """Return keyword dict for ``estimator.fit`` with early stopping."""
        if model_type == "lightgbm":
            import lightgbm as lgb

            return {
                "eval_set": [(X_val, y_val)],
                "callbacks": [lgb.early_stopping(stopping_rounds=es_rounds, verbose=False)],
            }
        if model_type == "xgboost":
            return {
                "eval_set": [(X_val, y_val)],
                "verbose": False,
            }
        if model_type == "catboost":
            return {
                "eval_set": (X_val, y_val),
                "early_stopping_rounds": es_rounds,
                "verbose": False,
            }
        return {}

    # ------------------------------------------------------------------ #
    # BaseForecaster interface
    # ------------------------------------------------------------------ #

    def fit(self, X, y_rev, y_cogs, eval_set=None, sample_weight=None):
        # ---- 1. Revenue model ----
        self.model_rev = self._build_estimator()
        rev_fit_kwargs = {}
        if eval_set is not None:
            X_val, y_rev_val, y_cogs_val = eval_set
            self._apply_early_stopping(self.model_rev, self._early_stopping_rounds)
            rev_fit_kwargs = self._fit_kwargs(
                self.model_type, self._early_stopping_rounds, X_val, y_rev_val
            )
        if sample_weight is not None:
            rev_fit_kwargs["sample_weight"] = sample_weight

        self.model_rev.fit(X, y_rev, **rev_fit_kwargs)

        # ---- 2. In-sample revenue predictions for COGS training ----
        rev_pred_train = self.model_rev.predict(X)
        X_cogs = X.copy()
        if isinstance(X_cogs, pd.DataFrame):
            X_cogs[self.PRED_REV_COL] = rev_pred_train
        else:
            X_cogs = np.column_stack([X_cogs, rev_pred_train])

        # ---- 3. COGS model (with predicted revenue as extra feature) ----
        self.model_cogs = self._build_estimator()
        cogs_fit_kwargs = {}
        if eval_set is not None:
            rev_pred_val = self.model_rev.predict(X_val)
            X_cogs_val = X_val.copy()
            if isinstance(X_cogs_val, pd.DataFrame):
                X_cogs_val[self.PRED_REV_COL] = rev_pred_val
            else:
                X_cogs_val = np.column_stack([X_cogs_val, rev_pred_val])
            self._apply_early_stopping(self.model_cogs, self._early_stopping_rounds)
            cogs_fit_kwargs = self._fit_kwargs(
                self.model_type, self._early_stopping_rounds, X_cogs_val, y_cogs_val
            )
        if sample_weight is not None:
            cogs_fit_kwargs["sample_weight"] = sample_weight

        self.model_cogs.fit(X_cogs, y_cogs, **cogs_fit_kwargs)

    def predict(self, X):
        rev_pred = self.model_rev.predict(X)
        X_cogs = X.copy()
        if isinstance(X_cogs, pd.DataFrame):
            X_cogs[self.PRED_REV_COL] = rev_pred
        else:
            X_cogs = np.column_stack([X_cogs, rev_pred])
        cogs_pred = self.model_cogs.predict(X_cogs)
        return rev_pred, cogs_pred

    def best_iterations(self) -> tuple[int | None, int | None]:
        rev_iter = None
        cogs_iter = None

        if self.model_rev is not None:
            if hasattr(self.model_rev, "best_iteration_"):
                rev_iter = int(self.model_rev.best_iteration_)
            elif hasattr(self.model_rev, "best_iteration"):
                rev_iter = int(self.model_rev.best_iteration)
            elif hasattr(self.model_rev, "get_best_iteration"):
                rev_iter = int(self.model_rev.get_best_iteration())

        if self.model_cogs is not None:
            if hasattr(self.model_cogs, "best_iteration_"):
                cogs_iter = int(self.model_cogs.best_iteration_)
            elif hasattr(self.model_cogs, "best_iteration"):
                cogs_iter = int(self.model_cogs.best_iteration)
            elif hasattr(self.model_cogs, "get_best_iteration"):
                cogs_iter = int(self.model_cogs.get_best_iteration())

        return rev_iter, cogs_iter

    def set_n_estimators(self, n_estimators: int) -> None:
        for model in (self.model_rev, self.model_cogs):
            if model is None:
                continue
            if hasattr(model, "n_estimators"):
                model.n_estimators = n_estimators
            elif hasattr(model, "set_params"):
                model.set_params(iterations=n_estimators)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self, f)

    @classmethod
    def load(cls, path: Path) -> Self:
        with open(path, "rb") as f:
            return pickle.load(f)
