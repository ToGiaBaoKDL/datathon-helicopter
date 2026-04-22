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
        self._cb_kwargs = cb_kwargs

    def fit(self, X, y_rev, y_cogs) -> None:
        self.model_rev = cb.CatBoostRegressor(**self._cb_kwargs)
        self.model_cogs = cb.CatBoostRegressor(**self._cb_kwargs)
        self.model_rev.fit(X, y_rev, verbose=False)
        self.model_cogs.fit(X, y_cogs, verbose=False)
