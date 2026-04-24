"""CatBoost forecaster implementation."""

from __future__ import annotations

import catboost as cb

from datathon.modeling.forecasters._dual_target_mixin import _DualTargetForecasterMixin
from datathon.modeling.forecasters.base import BaseForecaster


class CatBoostForecaster(_DualTargetForecasterMixin, BaseForecaster):
    """Separate CatBoostRegressor models for revenue and COGS."""

    def __init__(self, **cb_kwargs) -> None:
        self.model_rev: cb.CatBoostRegressor | None = None
        self.model_cogs: cb.CatBoostRegressor | None = None
        self._early_stopping_rounds = cb_kwargs.pop("early_stopping_rounds", 50)
        self._cb_kwargs = cb_kwargs

    def fit(self, X, y_rev, y_cogs, eval_set=None):
        self.model_rev = cb.CatBoostRegressor(**self._cb_kwargs)
        self.model_cogs = cb.CatBoostRegressor(**self._cb_kwargs)

        fit_rev: dict = {}
        fit_cogs: dict = {}
        if eval_set is not None:
            X_val, y_rev_val, y_cogs_val = eval_set
            fit_rev = {
                "eval_set": (X_val, y_rev_val),
                "early_stopping_rounds": self._early_stopping_rounds,
                "verbose": False,
            }
            fit_cogs = {
                "eval_set": (X_val, y_cogs_val),
                "early_stopping_rounds": self._early_stopping_rounds,
                "verbose": False,
            }

        self.model_rev.fit(X, y_rev, **fit_rev)
        self.model_cogs.fit(X, y_cogs, **fit_cogs)

    def best_iterations(self) -> tuple[int | None, int | None]:
        rev_iter = None
        cogs_iter = None
        if self.model_rev is not None and hasattr(self.model_rev, "get_best_iteration"):
            rev_iter = int(self.model_rev.get_best_iteration())
        if self.model_cogs is not None and hasattr(self.model_cogs, "get_best_iteration"):
            cogs_iter = int(self.model_cogs.get_best_iteration())
        return rev_iter, cogs_iter
