"""Generic training orchestrator for any BaseForecaster."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pandas as pd

from datathon.modeling.cv import ExpandingWindowCV, SlidingWindowCV
from datathon.modeling.forecasters.base import BaseForecaster
from datathon.modeling.metrics import fold_metrics
from datathon.modeling.recursive import feature_columns, recursive_forecast


class Trainer:
    """Train and cross-validate a ``BaseForecaster`` for revenue + COGS."""

    def __init__(
        self,
        forecaster: BaseForecaster,
        cv: ExpandingWindowCV | SlidingWindowCV,
        cogs_column: str = "cogs",
        target_transform: str = "identity",
    ):
        self.forecaster = forecaster
        self.cv = cv
        self.cogs_column = cogs_column
        self.cogs_is_ratio = cogs_column == "cogs_ratio"
        self.target_transform = target_transform

        if target_transform == "residual":
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
    ) -> dict[str, list[dict[str, float]]] | tuple[dict, list[pd.DataFrame]]:
        """Run expanding-window CV and return per-fold metrics."""
        df = df.copy().sort_values("sales_date").reset_index(drop=True)
        cols = feature_columns(df)

        results: dict[str, list[dict[str, float]]] = {"revenue": [], "cogs": []}
        fold_preds: list[pd.DataFrame] = []

        for fold, train_idx, val_idx in self.cv.split(df):
            train_df = df.iloc[train_idx]
            val_df = df.iloc[val_idx]

            fold_forecaster = copy.deepcopy(self.forecaster)
            fold_forecaster.fit(
                train_df[cols],
                train_df[self.revenue_column],
                train_df[self.cogs_column],
            )

            pred = recursive_forecast(
                fold_forecaster,
                train_df,
                val_df[["sales_date"]].rename(columns={"sales_date": "date"}),
                cols,
                cogs_is_ratio=self.cogs_is_ratio,
                target_transform=self.target_transform,
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
    ) -> tuple[BaseForecaster, list[str]]:
        """Train final models on the full historical dataset."""
        df = df.copy().sort_values("sales_date").reset_index(drop=True)
        cols = feature_columns(df)

        if n_estimators is not None:
            self.forecaster.set_n_estimators(n_estimators)

        self.forecaster.fit(df[cols], df[self.revenue_column], df[self.cogs_column])
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
    ) -> None:
        model_dir.mkdir(parents=True, exist_ok=True)

        meta = {
            "model_type": model_type,
            "feature_columns": feature_cols,
            "cogs_column": cogs_column,
            "target_transform": target_transform,
        }
        with open(model_dir / "meta.json", "w") as f:
            json.dump(meta, f, indent=2)

        forecaster.save(model_dir / "forecaster.pkl")

        if cv_results is not None:
            with open(model_dir / "cv_results.json", "w") as f:
                json.dump(cv_results, f, indent=2)

    @staticmethod
    def load_artifacts(
        model_dir: Path,
    ) -> tuple[BaseForecaster, list[str], str, str, str]:
        from datathon.modeling.forecasters import get_forecaster

        with open(model_dir / "meta.json") as f:
            meta = json.load(f)

        model_type = meta["model_type"]
        feature_cols = meta["feature_columns"]
        cogs_column = meta.get("cogs_column", "cogs")

        target_transform = meta.get("target_transform", "identity")

        forecaster_cls = get_forecaster(model_type)
        forecaster = forecaster_cls.load(model_dir / "forecaster.pkl")

        return forecaster, feature_cols, model_type, cogs_column, target_transform
