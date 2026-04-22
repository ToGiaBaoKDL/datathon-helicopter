"""Mixin for sklearn-like dual-target forecasters."""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Self

import numpy as np
import pandas as pd


class _DualTargetForecasterMixin:
    """Provides ``predict``, ``save``, and ``load`` for any forecaster
    that stores ``model_rev`` and ``model_cogs`` attributes.
    """

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
