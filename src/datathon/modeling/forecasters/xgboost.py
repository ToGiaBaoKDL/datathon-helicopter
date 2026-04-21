"""XGBoost forecaster implementation."""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Self

import numpy as np
import pandas as pd
import xgboost as xgb

from datathon.modeling.forecasters.base import BaseForecaster


class XGBoostForecaster(BaseForecaster):
    """Separate XGBRegressor models for revenue and COGS."""

    def __init__(self, **xgb_kwargs) -> None:
        self.model_rev: xgb.XGBRegressor | None = None
        self.model_cogs: xgb.XGBRegressor | None = None
        self._xgb_kwargs = xgb_kwargs

    def fit(self, X: pd.DataFrame, y_rev: pd.Series, y_cogs: pd.Series) -> None:
        self.model_rev = xgb.XGBRegressor(**self._xgb_kwargs)
        self.model_cogs = xgb.XGBRegressor(**self._xgb_kwargs)
        self.model_rev.fit(X, y_rev)
        self.model_cogs.fit(X, y_cogs)

    def predict(self, X: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        if self.model_rev is None or self.model_cogs is None:
            raise RuntimeError("Forecaster has not been fitted yet.")
        return self.model_rev.predict(X), self.model_cogs.predict(X)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self, f)

    @classmethod
    def load(cls, path: Path) -> Self:
        with open(path, "rb") as f:
            return pickle.load(f)
