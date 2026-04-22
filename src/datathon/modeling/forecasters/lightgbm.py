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
        self._lgbm_kwargs = lgbm_kwargs

    def fit(self, X, y_rev, y_cogs) -> None:
        self.model_rev = lgb.LGBMRegressor(**self._lgbm_kwargs)
        self.model_cogs = lgb.LGBMRegressor(**self._lgbm_kwargs)
        self.model_rev.fit(X, y_rev)
        self.model_cogs.fit(X, y_cogs)
