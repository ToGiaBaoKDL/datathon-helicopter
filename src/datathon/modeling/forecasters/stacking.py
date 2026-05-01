"""Stacking ensemble forecaster with HuberRegressor meta-learners."""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Self

import numpy as np
import pandas as pd

from datathon.modeling.forecasters.base import BaseForecaster


class StackingForecaster(BaseForecaster):
    """Stacking ensemble: base models + HuberRegressor meta-learners.

    Parameters
    ----------
    members:
        List of fitted base forecasters.
    meta_rev:
        Fitted meta-learner for revenue (e.g. HuberRegressor).
    meta_cogs:
        Fitted meta-learner for COGS.
    """

    def __init__(
        self,
        members: list[BaseForecaster],
        meta_rev: object,
        meta_cogs: object,
    ) -> None:
        self.members = members
        self.meta_rev = meta_rev
        self.meta_cogs = meta_cogs

    def _meta_predict(self, meta, X_meta):
        """Call meta-learner predict, supporting both sklearn-style
        estimators and simple weight arrays."""
        if hasattr(meta, "predict"):
            return meta.predict(X_meta)
        # meta is a 1-D weight array → weighted average
        w = np.asarray(meta, dtype=float)
        return np.average(X_meta, axis=1, weights=w)

    def fit(self, X, y_rev, y_cogs, eval_set=None, **kwargs):
        """Fit all base models.  Meta-learners are assumed pre-fitted."""
        for member in self.members:
            member.fit(X, y_rev, y_cogs, eval_set=eval_set, **kwargs)

    def predict(self, X: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        rev_preds = []
        cogs_preds = []
        for member in self.members:
            rev, cogs = member.predict(X)
            rev_preds.append(rev)
            cogs_preds.append(cogs)
        X_meta_rev = np.column_stack(rev_preds)
        X_meta_cogs = np.column_stack(cogs_preds)
        final_rev = self._meta_predict(self.meta_rev, X_meta_rev)
        final_cogs = self._meta_predict(self.meta_cogs, X_meta_cogs)
        return final_rev, final_cogs

    def best_iterations(self) -> tuple[int | None, int | None]:
        all_rev = []
        all_cogs = []
        for member in self.members:
            rev_iter, cogs_iter = member.best_iterations()
            if rev_iter is not None:
                all_rev.append(rev_iter)
            if cogs_iter is not None:
                all_cogs.append(cogs_iter)
        return (max(all_rev) if all_rev else None, max(all_cogs) if all_cogs else None)

    def set_n_estimators(self, n_estimators: int) -> None:
        for member in self.members:
            member.set_n_estimators(n_estimators)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self, f)

    @classmethod
    def load(cls, path: Path) -> Self:
        with open(path, "rb") as f:
            return pickle.load(f)
