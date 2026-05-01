"""LightGBM forecaster implementation."""

from __future__ import annotations

import lightgbm as lgb

from datathon.modeling.forecasters._dual_target_mixin import _DualTargetForecasterMixin
from datathon.modeling.forecasters.base import BaseForecaster


class LightGBMForecaster(_DualTargetForecasterMixin, BaseForecaster):
    """Separate LGBMRegressor models for revenue and COGS."""

    def __init__(self, **lgbm_kwargs) -> None:
        self.model_rev: lgb.LGBMRegressor | None = None
        self.model_cogs: lgb.LGBMRegressor | None = None
        self._early_stopping_rounds = lgbm_kwargs.pop("early_stopping_rounds", 50)
        self._lgbm_kwargs = lgbm_kwargs

    def fit(self, X, y_rev, y_cogs, eval_set=None, sample_weight=None):
        rev_kwargs = dict(self._lgbm_kwargs)
        cogs_kwargs = dict(self._lgbm_kwargs)
        if "random_state" not in rev_kwargs:
            rev_kwargs["random_state"] = 42
        if "random_state" not in cogs_kwargs:
            cogs_kwargs["random_state"] = 42
        self.model_rev = lgb.LGBMRegressor(**rev_kwargs)
        self.model_cogs = lgb.LGBMRegressor(**cogs_kwargs)

        fit_rev: dict = {}
        fit_cogs: dict = {}
        if eval_set is not None:
            X_val, y_rev_val, y_cogs_val = eval_set
            fit_rev = {
                "eval_set": [(X_val, y_rev_val)],
                "callbacks": [
                    lgb.early_stopping(stopping_rounds=self._early_stopping_rounds, verbose=False)
                ],
            }
            fit_cogs = {
                "eval_set": [(X_val, y_cogs_val)],
                "callbacks": [
                    lgb.early_stopping(stopping_rounds=self._early_stopping_rounds, verbose=False)
                ],
            }

        if sample_weight is not None:
            fit_rev["sample_weight"] = sample_weight
            fit_cogs["sample_weight"] = sample_weight

        self.model_rev.fit(X, y_rev, **fit_rev)
        self.model_cogs.fit(X, y_cogs, **fit_cogs)

    def best_iterations(self) -> tuple[int | None, int | None]:
        rev_iter = None
        cogs_iter = None
        if self.model_rev is not None and hasattr(self.model_rev, "best_iteration_"):
            rev_iter = int(self.model_rev.best_iteration_)
        if self.model_cogs is not None and hasattr(self.model_cogs, "best_iteration_"):
            cogs_iter = int(self.model_cogs.best_iteration_)
        return rev_iter, cogs_iter

    def set_n_estimators(self, n_estimators: int) -> None:
        if self.model_rev is not None:
            self.model_rev.n_estimators = n_estimators
        if self.model_cogs is not None:
            self.model_cogs.n_estimators = n_estimators
