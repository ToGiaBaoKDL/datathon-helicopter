"""Ensemble forecaster that averages predictions from multiple forecasters."""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Self

import numpy as np
import pandas as pd

from datathon.modeling.forecasters.base import BaseForecaster


class EnsembleForecaster(BaseForecaster):
    """Average predictions from a list of fitted ``BaseForecaster`` instances.

    Each member forecaster must already be fitted. ``fit`` is a no-op;
    ensemble weights are fixed at construction time.
    """

    def __init__(
        self,
        members: list[BaseForecaster],
        weights: list[float] | None = None,
    ) -> None:
        if not members:
            raise ValueError("Ensemble must contain at least one forecaster.")
        self.members = members
        if weights is None:
            weights = [1.0 / len(members)] * len(members)
        if len(weights) != len(members):
            raise ValueError("weights and members must have the same length.")
        total = sum(weights)
        self.weights = [w / total for w in weights]

    def fit(self, X: pd.DataFrame, y_rev: pd.Series, y_cogs: pd.Series) -> None:
        """No-op: members are assumed pre-fitted."""
        return

    def predict(self, X: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        rev_preds = np.zeros(len(X))
        cogs_preds = np.zeros(len(X))
        for member, weight in zip(self.members, self.weights, strict=True):
            rev, cogs = member.predict(X)
            rev_preds += weight * rev
            cogs_preds += weight * cogs
        return rev_preds, cogs_preds

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self, f)

    @classmethod
    def load(cls, path: Path) -> Self:
        with open(path, "rb") as f:
            return pickle.load(f)
