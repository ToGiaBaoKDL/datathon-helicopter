"""Generic training orchestrator for any BaseForecaster."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from datathon.modeling.cv import ExpandingWindowCV, SlidingWindowCV
from datathon.modeling.forecasters.base import BaseForecaster
from datathon.modeling.metrics import fold_metrics
from datathon.modeling.recursive import (
    _PYTHON_ONLY_FEATURES,
    _STATIC_FEATURES,
    _backfill_historical_features,
    _ensure_columns,
    direct_forecast,
    feature_columns,
    recursive_forecast,
)


class Trainer:
    """Train and cross-validate a ``BaseForecaster`` for revenue + COGS."""

    def __init__(
        self,
        forecaster: BaseForecaster,
        cv: ExpandingWindowCV | SlidingWindowCV,
        cogs_column: str = "cogs",
        target_transform: str = "identity",
        forecast_mode: str = "recursive",
    ):
        self.forecaster = forecaster
        self.cv = cv
        self.cogs_column = cogs_column
        self.cogs_is_ratio = cogs_column == "cogs_ratio"
        self.target_transform = target_transform
        self.forecast_mode = forecast_mode
        self._last_cv_best_iters: list[tuple[int | None, int | None]] = []

        if target_transform in ("residual", "log_residual"):
            self.revenue_column = "revenue_residual"
        elif target_transform == "log":
            self.revenue_column = "log_revenue"
        else:
            self.revenue_column = "revenue"

    def run_cv(
        self,
        df: pd.DataFrame,
        *,
        return_predictions: bool = False,
        tracker=None,
        sample_weight: bool = False,
        restart_horizon: int | None = None,
    ) -> dict[str, list[dict[str, float]]] | tuple[dict, list[pd.DataFrame]]:
        """Run expanding-window CV and return per-fold metrics."""
        df = df.copy().sort_values("sales_date").reset_index(drop=True)
        _ensure_columns(df, _PYTHON_ONLY_FEATURES)
        # NOTE: _backfill_historical_features is applied per-fold below to
        # avoid leakage from validation data into training EMAs/trends.
        base_cols = feature_columns(df)
        if self.forecast_mode == "direct":
            base_cols = [c for c in base_cols if c in _STATIC_FEATURES]

        results: dict[str, list[dict[str, float]]] = {"revenue": [], "cogs": []}
        fold_preds: list[pd.DataFrame] = []
        self._last_cv_best_iters.clear()

        for fold, train_idx, val_idx in self.cv.split(df):
            train_df = df.iloc[train_idx].copy()
            val_df = df.iloc[val_idx]

            _backfill_historical_features(train_df)
            cols = [c for c in base_cols if c in train_df.columns]

            sw = None
            if sample_weight:
                max_days = (train_df["sales_date"].max() - train_df["sales_date"]).dt.days
                sw = np.exp(-0.001 * max_days.to_numpy())
                sw = sw / sw.sum() * len(sw)

            fold_forecaster = copy.deepcopy(self.forecaster)
            fold_forecaster.fit(
                train_df[cols],
                train_df[self.revenue_column],
                train_df[self.cogs_column],
                eval_set=(val_df[cols], val_df[self.revenue_column], val_df[self.cogs_column]),
                sample_weight=sw,
            )
            self._last_cv_best_iters.append(fold_forecaster.best_iterations())

            # Pass the full validation frame (renamed to 'date') so that
            # _prepare_future_frame can pull known-in-advance columns such
            # as promo features for each validation day instead of freezing
            # the last training observation.
            val_scaffold = val_df.rename(columns={"sales_date": "date"})
            if self.forecast_mode == "direct":
                pred = direct_forecast(
                    fold_forecaster,
                    train_df,
                    val_scaffold,
                    cols,
                    cogs_is_ratio=self.cogs_is_ratio,
                    target_transform=self.target_transform,
                )
            else:
                pred = recursive_forecast(
                    fold_forecaster,
                    train_df,
                    val_scaffold,
                    cols,
                    cogs_is_ratio=self.cogs_is_ratio,
                    target_transform=self.target_transform,
                    restart_horizon=restart_horizon,
                )

            actual = val_df[["sales_date", "revenue", "cogs"]].copy()
            actual = actual.rename(columns={"sales_date": "date"})
            merged = actual.merge(pred, on="date", suffixes=("_actual", "_pred"))

            fold_result: dict[str, float] = {}
            for target in ("revenue", "cogs"):
                y_true = merged[f"{target}_actual"].to_numpy()
                y_pred = merged[f"{target}_pred"].to_numpy()

                m = fold_metrics(y_true, y_pred)
                results[target].append(
                    {"fold": fold + 1, "mae": m["mae"], "rmse": m["rmse"], "r2": m["r2"]}
                )
                fold_result[target] = m["mae"]

                if tracker is not None:
                    tracker.log_metric(f"cv_{target}_mae", m["mae"], step=fold)
                    tracker.log_metric(f"cv_{target}_rmse", m["rmse"], step=fold)
                    tracker.log_metric(f"cv_{target}_r2", m["r2"], step=fold)

            if tracker is not None:
                tracker.log_metric(
                    "cv_fold_total_mae",
                    fold_result["revenue"] + fold_result["cogs"],
                    step=fold,
                )

            if return_predictions:
                fold_preds.append(merged[["date", "revenue_pred", "cogs_pred"]].copy())

        if return_predictions:
            return results, fold_preds
        return results

    def train_final(
        self,
        df: pd.DataFrame,
        *,
        n_estimators: int | None = None,
        sample_weight: bool = False,
    ) -> tuple[BaseForecaster, list[str]]:
        """Train final models on the full historical dataset."""
        df = df.copy().sort_values("sales_date").reset_index(drop=True)
        _ensure_columns(df, _PYTHON_ONLY_FEATURES)
        _backfill_historical_features(df)
        cols = feature_columns(df)
        if self.forecast_mode == "direct":
            cols = [c for c in cols if c in _STATIC_FEATURES]

        sw = None
        if sample_weight:
            max_days = (df["sales_date"].max() - df["sales_date"]).dt.days
            sw = np.exp(-0.001 * max_days.to_numpy())
            sw = sw / sw.sum() * len(sw)

        if n_estimators is None and self._last_cv_best_iters:
            all_iters = [b for pair in self._last_cv_best_iters for b in pair if b is not None]
            if all_iters:
                n_estimators = int(max(all_iters))

        if n_estimators is not None:
            self.forecaster.set_n_estimators(n_estimators)

        self.forecaster.fit(
            df[cols], df[self.revenue_column], df[self.cogs_column], sample_weight=sw
        )
        return self.forecaster, cols

    @staticmethod
    def save_artifacts(
        model_dir: Path,
        forecaster: BaseForecaster,
        feature_cols: list[str],
        model_type: str,
        cv_results: dict | None = None,
        cogs_column: str = "cogs",
        target_transform: str = "identity",
        sequential_cogs: bool = False,
        restart_horizon: int | None = None,
        forecast_mode: str = "recursive",
        spike_classifier=None,
    ) -> None:
        model_dir.mkdir(parents=True, exist_ok=True)

        meta = {
            "model_type": model_type,
            "feature_columns": feature_cols,
            "cogs_column": cogs_column,
            "target_transform": target_transform,
            "sequential_cogs": sequential_cogs,
            "restart_horizon": restart_horizon,
            "forecast_mode": forecast_mode,
            "has_spike_classifier": spike_classifier is not None,
        }
        with open(model_dir / "meta.json", "w") as f:
            json.dump(meta, f, indent=2)

        forecaster.save(model_dir / "forecaster.pkl")

        if spike_classifier is not None:
            spike_classifier.save(model_dir / "spike_classifier.pkl")

        if cv_results is not None:
            with open(model_dir / "cv_results.json", "w") as f:
                json.dump(cv_results, f, indent=2)

    @staticmethod
    def load_artifacts(
        model_dir: Path,
    ) -> tuple[BaseForecaster, list[str], str, str, str, bool, int | None, str, Any]:
        from datathon.modeling.forecasters import get_forecaster
        from datathon.modeling.forecasters.sequential import SequentialForecaster

        with open(model_dir / "meta.json") as f:
            meta = json.load(f)

        model_type = meta["model_type"]
        feature_cols = meta["feature_columns"]
        cogs_column = meta.get("cogs_column", "cogs")
        target_transform = meta.get("target_transform", "identity")
        sequential_cogs = meta.get("sequential_cogs", False)
        restart_horizon = meta.get("restart_horizon", None)
        forecast_mode = meta.get("forecast_mode", "recursive")
        has_spike = meta.get("has_spike_classifier", False)

        if model_type == "stacked":
            from datathon.modeling.forecasters.stacking import StackingForecaster

            forecaster = StackingForecaster.load(model_dir / "forecaster.pkl")
        elif sequential_cogs:
            forecaster = SequentialForecaster.load(model_dir / "forecaster.pkl")
        else:
            forecaster_cls = get_forecaster(model_type)
            forecaster = forecaster_cls.load(model_dir / "forecaster.pkl")

        spike_classifier = None
        if has_spike and (model_dir / "spike_classifier.pkl").exists():
            from datathon.modeling.spike_classifier import SpikeClassifier

            spike_classifier = SpikeClassifier.load(model_dir / "spike_classifier.pkl")

        return (
            forecaster,
            feature_cols,
            model_type,
            cogs_column,
            target_transform,
            sequential_cogs,
            restart_horizon,
            forecast_mode,
            spike_classifier,
        )
