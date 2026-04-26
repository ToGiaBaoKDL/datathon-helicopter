"""Time-series cross-validation: expanding and sliding window variants."""

from __future__ import annotations

import pandas as pd


class ExpandingWindowCV:
    """Expanding-window time-series CV.

    Each fold grows the training set by ``horizon_days`` while keeping the
    validation window fixed:

        Fold 0: train=[0..T0],        val=[T0..T0+H]
        Fold 1: train=[0..T0+H],      val=[T0+H..T0+2H]
        ...

    Use this only when the data-generating process is stable (no concept drift).
    For this dataset, sliding window is the default because the
    ``days_since_2019`` feature indicates a structural break.

    Parameters
    ----------
    n_folds:
        Number of CV folds.
    horizon_days:
        Length of each validation window (and step by which the train set grows).
    purge_days:
        Gap between train_end and val_start. Recommended 7–14 days to
        reduce autocorrelation leakage through lag/rolling features.
    """

    def __init__(
        self,
        n_folds: int = 5,
        horizon_days: int = 30,
        purge_days: int = 0,
    ):
        self.n_folds = n_folds
        self.horizon_days = horizon_days
        self.purge_days = purge_days

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
            val_start = train_end + self.purge_days
            val_end = min(val_start + self.horizon_days, n)

            train_idx = list(range(train_end))
            val_idx = list(range(val_start, val_end))

            if not val_idx:
                break

            yield fold, train_idx, val_idx


class SlidingWindowCV:
    """Sliding-window time-series CV.

    The training window is kept at a fixed size. This is preferred when the
    data distribution drifts over time (concept drift, structural breaks)
    because older patterns can harm rather than help the model.

    For this dataset (2015–2022) a structural break around 2019 is captured
    by ``days_since_2019``, making sliding window generally more reliable
    than expanding window.

    Recommended::

        SlidingWindowCV(
            n_folds=2,
            train_window_days=1096,   # ~3 years ≈ 2× horizon
            horizon_days=548,         # real forecast horizon
            purge_days=7,             # reduce lag-feature leakage
        )

    Parameters
    ----------
    n_folds:
        Number of CV folds. With train_window=1096 and horizon=548 on
        ~2900 rows, 2 folds is the practical maximum.
    train_window_days:
        Fixed training window (days). Rule of thumb: 2–3× forecast horizon.
    horizon_days:
        Length of each validation window. Should match the real forecast
        horizon (548 days for this competition).
    purge_days:
        Gap between train_end and val_start. Recommended 7–14 days to
        reduce autocorrelation leakage through lag/rolling features.
    """

    def __init__(
        self,
        n_folds: int = 4,
        train_window_days: int = 1096,
        horizon_days: int = 365,
        purge_days: int = 7,
    ):
        self.n_folds = n_folds
        self.train_window_days = train_window_days
        self.horizon_days = horizon_days
        self.purge_days = purge_days

    def split(self, df: pd.DataFrame):
        n = len(df)
        total_val = self.n_folds * self.horizon_days
        min_start = n - total_val

        if min_start <= 0:
            raise ValueError(
                f"Not enough rows ({n}) for {self.n_folds} folds of "
                f"{self.horizon_days} days each (need at least {total_val} rows)."
            )

        for fold in range(self.n_folds):
            val_end = n - fold * self.horizon_days
            val_start = max(0, val_end - self.horizon_days)
            train_end = val_start - self.purge_days
            train_start = max(0, train_end - self.train_window_days)

            train_idx = list(range(train_start, train_end))
            val_idx = list(range(val_start, val_end))

            if not val_idx or not train_idx:
                break

            yield fold, train_idx, val_idx


def build_cv(
    n_folds: int,
    horizon_days: int,
    cv_type: str,
    train_window_days: int = 1096,
    purge_days: int = 0,
) -> ExpandingWindowCV | SlidingWindowCV:
    """Factory: build the requested CV strategy."""
    if cv_type == "sliding":
        return SlidingWindowCV(
            n_folds=n_folds,
            train_window_days=train_window_days,
            horizon_days=horizon_days,
            purge_days=purge_days,
        )
    return ExpandingWindowCV(n_folds=n_folds, horizon_days=horizon_days, purge_days=purge_days)
