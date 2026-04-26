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
    def fit(
        self,
        X: pd.DataFrame,
        y_rev: pd.Series,
        y_cogs: pd.Series,
        eval_set: tuple[pd.DataFrame, pd.Series, pd.Series] | None = None,
    ) -> None:
        """Fit the forecaster on training features and dual targets.

        Parameters
        ----------
        eval_set:
            Optional validation tuple ``(X_val, y_rev_val, y_cogs_val)``.
            When provided, the implementation should use early stopping
            based on the validation loss.
        """

    @abstractmethod
    def predict(self, X: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        """Return (revenue_pred, cogs_pred) arrays for the given feature rows."""

    @abstractmethod
    def save(self, path: Path) -> None:
        """Persist the fitted forecaster to *path*."""

    def best_iterations(self) -> tuple[int | None, int | None]:
        """Return (best_iteration_rev, best_iteration_cogs) if available."""
        return None, None

    @classmethod
    @abstractmethod
    def load(cls, path: Path) -> Self:
        """Restore a forecaster previously saved with :meth:`save`."""

    def set_n_estimators(self, n_estimators: int) -> None:
        """Override the number of boosting rounds without re-fitting.

        Used by :meth:`Trainer.train_final` when the iteration count has already
        been validated via CV / tuning, so the final model can be fit on the full
        dataset without an early-stopping holdout.
        """
        raise NotImplementedError(f"{type(self).__name__} does not support set_n_estimators.")
