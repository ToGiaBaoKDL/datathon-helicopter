"""Spike classifier: detect high-revenue days and apply empirical boost."""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


class SpikeClassifier:
    """XGBoost classifier that detects revenue spike days and boosts predictions.

    A *spike day* is defined as any day with revenue above the historical
    90th percentile.  The classifier is trained on the same feature set as
    the revenue regressor.  At inference time the predicted spike
    probability is used to up-weight the base revenue prediction:

        revenue_boosted = base_pred * (1 + P_spike * alpha * (boost - 1))

    where ``boost = mean(spike_days) / mean(normal_days)`` and ``alpha``
    is a damping factor (default 0.6) to avoid over-boosting.
    """

    def __init__(
        self,
        quantile: float = 0.90,
        alpha: float = 0.6,
        max_boost: float = 1.3,
        n_estimators: int = 900,
        learning_rate: float = 0.05,
        max_depth: int = 2,
        min_child_weight: int = 7,
        gamma: float = 1.0,
        subsample: float = 1.0,
        colsample_bytree: float = 0.85,
        reg_alpha: float = 0.0,
        reg_lambda: float = 5.0,
        random_state: int = 42,
    ) -> None:
        self.quantile = quantile
        self.alpha = alpha
        self.max_boost = max_boost
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.max_depth = max_depth
        self.min_child_weight = min_child_weight
        self.gamma = gamma
        self.subsample = subsample
        self.colsample_bytree = colsample_bytree
        self.reg_alpha = reg_alpha
        self.reg_lambda = reg_lambda
        self.random_state = random_state

        self.model_: Any | None = None
        self.threshold_: float | None = None
        self.empirical_boost_: float | None = None

    def fit(self, X: pd.DataFrame, y_revenue: pd.Series) -> SpikeClassifier:
        """Fit the spike classifier on historical revenue.

        Parameters
        ----------
        X:
            Feature matrix (same features as revenue regressor).
        y_revenue:
            Raw historical revenue.
        """
        self.threshold_ = float(y_revenue.quantile(self.quantile))
        is_spike = (y_revenue > self.threshold_).astype(int)

        n_pos = is_spike.sum()
        n_neg = len(is_spike) - n_pos
        scale_pos_weight = n_neg / n_pos if n_pos > 0 else 1.0

        try:
            from xgboost import XGBClassifier
        except ImportError as exc:
            raise RuntimeError(
                "SpikeClassifier requires xgboost. Install with: uv add xgboost"
            ) from exc

        self.model_ = XGBClassifier(
            n_estimators=self.n_estimators,
            learning_rate=self.learning_rate,
            max_depth=self.max_depth,
            min_child_weight=self.min_child_weight,
            gamma=self.gamma,
            subsample=self.subsample,
            colsample_bytree=self.colsample_bytree,
            reg_alpha=self.reg_alpha,
            reg_lambda=self.reg_lambda,
            scale_pos_weight=scale_pos_weight,
            random_state=self.random_state,
            eval_metric="logloss",
            use_label_encoder=False,
            verbosity=0,
        )
        self.model_.fit(X.fillna(0), is_spike)

        # Empirical boost factor
        spike_mean = float(y_revenue[is_spike == 1].mean()) if n_pos > 0 else 1.0
        normal_mean = float(y_revenue[is_spike == 0].mean()) if n_neg > 0 else 1.0
        self.empirical_boost_ = spike_mean / normal_mean if normal_mean > 0 else 1.0
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Return spike probability for each row."""
        if self.model_ is None:
            raise RuntimeError("SpikeClassifier has not been fitted yet. Call fit() first.")
        return self.model_.predict_proba(X.fillna(0))[:, 1]

    def apply_boost(
        self,
        base_pred: np.ndarray,
        spike_prob: np.ndarray,
    ) -> np.ndarray:
        """Apply empirical boost to base revenue predictions."""
        if self.empirical_boost_ is None:
            raise RuntimeError("SpikeClassifier has not been fitted yet. Call fit() first.")

        boost = 1.0 + spike_prob * self.alpha * (self.empirical_boost_ - 1.0)
        boost = np.clip(boost, 1.0, self.max_boost)
        return base_pred * boost

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self, f)

    @classmethod
    def load(cls, path: Path) -> SpikeClassifier:
        with open(path, "rb") as f:
            return pickle.load(f)
