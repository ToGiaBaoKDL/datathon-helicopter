"""Ensemble forecaster that averages predictions from multiple models."""

from __future__ import annotations

from pathlib import Path
from typing import Self

import numpy as np

from datathon.modeling.forecasters.base import BaseForecaster


class EnsembleForecaster(BaseForecaster):
    """Average predictions from multiple ``BaseForecaster`` instances.

    Parameters
    ----------
    members:
        List of fitted forecasters.
    weights:
        Optional list of weights (one per member).  When ``None`` an
        unweighted average is used.
    """

    def __init__(self, members: list[BaseForecaster], weights: list[float] | None = None):
        self.members = members
        if weights is not None and len(weights) != len(members):
            raise ValueError("weights must have same length as members")
        self.weights = weights

    def fit(self, X, y_rev, y_cogs, eval_set=None, **kwargs):
        """No-op: ensemble assumes members are already fitted."""
        pass

    def predict(self, X) -> tuple[np.ndarray, np.ndarray]:
        rev_preds = []
        cogs_preds = []
        for member in self.members:
            rev, cogs = member.predict(X)
            rev_preds.append(rev)
            cogs_preds.append(cogs)

        rev_stack = np.stack(rev_preds, axis=0)
        cogs_stack = np.stack(cogs_preds, axis=0)

        if self.weights is None:
            rev_avg = rev_stack.mean(axis=0)
            cogs_avg = cogs_stack.mean(axis=0)
        else:
            w = np.array(self.weights, dtype=float)
            w = w / w.sum()
            rev_avg = np.average(rev_stack, axis=0, weights=w)
            cogs_avg = np.average(cogs_stack, axis=0, weights=w)

        return rev_avg, cogs_avg

    def save(self, path: Path) -> None:
        # Ensemble is ephemeral; members are saved individually.
        pass

    @classmethod
    def load(cls, path: Path) -> Self:
        raise NotImplementedError("EnsembleForecaster does not support standalone load.")
