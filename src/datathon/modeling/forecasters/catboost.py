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
        rev_kwargs = dict(self._cb_kwargs)
        cogs_kwargs = dict(self._cb_kwargs)
        # Ensure reproducibility
        if "random_seed" not in rev_kwargs and "random_state" not in rev_kwargs:
            rev_kwargs["random_seed"] = 42
        if "random_seed" not in cogs_kwargs and "random_state" not in cogs_kwargs:
            cogs_kwargs["random_seed"] = 42
        self.model_rev = cb.CatBoostRegressor(**rev_kwargs)
        self.model_cogs = cb.CatBoostRegressor(**cogs_kwargs)

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

    def set_n_estimators(self, n_estimators: int) -> None:
        if self.model_rev is not None:
            self.model_rev.set_params(iterations=n_estimators)
        if self.model_cogs is not None:
            self.model_cogs.set_params(iterations=n_estimators)
