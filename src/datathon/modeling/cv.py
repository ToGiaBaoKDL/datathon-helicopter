"""Time-series expanding-window cross-validation."""

from __future__ import annotations

import pandas as pd


class ExpandingWindowCV:
    """Time-series expanding-window cross-validation."""

    def __init__(self, n_folds: int = 5, horizon_days: int = 30):
        self.n_folds = n_folds
        self.horizon_days = horizon_days

    def split(self, df: pd.DataFrame):
        n = len(df)
        total_val = self.n_folds * self.horizon_days
        min_train_size = n - total_val
        if min_train_size <= 0:
            raise ValueError(
                f"Not enough rows ({n}) for {self.n_folds} folds of {self.horizon_days} days each."
            )

        for fold in range(self.n_folds):
            train_end = min_train_size + fold * self.horizon_days
            val_start = train_end
            val_end = min(train_end + self.horizon_days, n)

            train_idx = list(range(train_end))
            val_idx = list(range(val_start, val_end))

            if not val_idx:
                break

            yield fold, train_idx, val_idx
