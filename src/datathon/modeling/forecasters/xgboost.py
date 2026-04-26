"""XGBoost forecaster implementation."""

from __future__ import annotations

import xgboost as xgb

from datathon.modeling.forecasters._dual_target_mixin import _DualTargetForecasterMixin
from datathon.modeling.forecasters.base import BaseForecaster


class XGBoostForecaster(_DualTargetForecasterMixin, BaseForecaster):
    """Separate XGBRegressor models for revenue and COGS."""

    def __init__(self, **xgb_kwargs) -> None:
        self.model_rev: xgb.XGBRegressor | None = None
        self.model_cogs: xgb.XGBRegressor | None = None
        self._early_stopping_rounds = xgb_kwargs.pop("early_stopping_rounds", 50)
        self._xgb_kwargs = xgb_kwargs

    def fit(self, X, y_rev, y_cogs, eval_set=None):
        rev_kwargs = dict(self._xgb_kwargs)
        cogs_kwargs = dict(self._xgb_kwargs)
        # Ensure reproducibility
        if "random_state" not in rev_kwargs:
            rev_kwargs["random_state"] = 42
        if "random_state" not in cogs_kwargs:
            cogs_kwargs["random_state"] = 42

        if eval_set is not None:
            X_val, y_rev_val, y_cogs_val = eval_set
            rev_kwargs["callbacks"] = [
                xgb.callback.EarlyStopping(rounds=self._early_stopping_rounds)
            ]
            cogs_kwargs["callbacks"] = [
                xgb.callback.EarlyStopping(rounds=self._early_stopping_rounds)
            ]
            fit_rev = {"eval_set": [(X_val, y_rev_val)], "verbose": False}
            fit_cogs = {"eval_set": [(X_val, y_cogs_val)], "verbose": False}
        else:
            fit_rev = {}
            fit_cogs = {}

        self.model_rev = xgb.XGBRegressor(**rev_kwargs)
        self.model_cogs = xgb.XGBRegressor(**cogs_kwargs)

        self.model_rev.fit(X, y_rev, **fit_rev)
        self.model_cogs.fit(X, y_cogs, **fit_cogs)

    def best_iterations(self) -> tuple[int | None, int | None]:
        rev_iter = None
        cogs_iter = None
        if self.model_rev is not None and hasattr(self.model_rev, "best_iteration"):
            rev_iter = int(self.model_rev.best_iteration)
        if self.model_cogs is not None and hasattr(self.model_cogs, "best_iteration"):
            cogs_iter = int(self.model_cogs.best_iteration)
        return rev_iter, cogs_iter

    def set_n_estimators(self, n_estimators: int) -> None:
        if self.model_rev is not None:
            self.model_rev.n_estimators = n_estimators
        if self.model_cogs is not None:
            self.model_cogs.n_estimators = n_estimators
