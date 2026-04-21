"""Base forecaster abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Self

import numpy as np
import pandas as pd


class BaseForecaster(ABC):
    """Abstract base class for daily revenue + COGS forecasters."""

    @abstractmethod
    def fit(self, X: pd.DataFrame, y_rev: pd.Series, y_cogs: pd.Series) -> None:
        """Fit the forecaster on training features and dual targets."""

    @abstractmethod
    def predict(self, X: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        """Return (revenue_pred, cogs_pred) arrays for the given feature rows."""

    @abstractmethod
    def save(self, path: Path) -> None:
        """Persist the fitted forecaster to *path*."""

    @classmethod
    @abstractmethod
    def load(cls, path: Path) -> Self:
        """Restore a forecaster previously saved with :meth:`save`."""
