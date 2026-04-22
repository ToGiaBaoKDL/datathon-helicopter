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

    def fit(self, X, y_rev, y_cogs, eval_set=None):
        self.model_rev = lgb.LGBMRegressor(**self._lgbm_kwargs)
        self.model_cogs = lgb.LGBMRegressor(**self._lgbm_kwargs)

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

        self.model_rev.fit(X, y_rev, **fit_rev)
        self.model_cogs.fit(X, y_cogs, **fit_cogs)
