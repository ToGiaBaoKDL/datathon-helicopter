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
        self._xgb_kwargs = xgb_kwargs

    def fit(self, X, y_rev, y_cogs) -> None:
        self.model_rev = xgb.XGBRegressor(**self._xgb_kwargs)
        self.model_cogs = xgb.XGBRegressor(**self._xgb_kwargs)
        self.model_rev.fit(X, y_rev)
        self.model_cogs.fit(X, y_cogs)
