"""Generic training orchestrator for any BaseForecaster."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from datathon.modeling.cv import ExpandingWindowCV
from datathon.modeling.forecasters.base import BaseForecaster
from datathon.modeling.recursive import feature_columns, recursive_forecast


class Trainer:
    """Train and cross-validate a ``BaseForecaster`` for revenue + COGS."""

    def __init__(
        self,
        forecaster: BaseForecaster,
        cv: ExpandingWindowCV,
        cogs_column: str = "cogs",
        residual_target: bool = False,
    ):
        self.forecaster = forecaster
        self.cv = cv
        self.cogs_column = cogs_column
        self.cogs_is_ratio = cogs_column == "cogs_ratio"
        self.residual_target = residual_target
        self.revenue_column = "revenue_residual" if residual_target else "revenue"

    def run_cv(
        self, df: pd.DataFrame, *, return_predictions: bool = False
    ) -> dict[str, list[dict[str, float]]] | tuple[dict, list[pd.DataFrame]]:
        """Run expanding-window CV and return per-fold metrics.

        Parameters
        ----------
        return_predictions:
            When ``True``, also return a list of prediction DataFrames
            (one per fold) with columns ``date``, ``revenue_pred``,
            ``cogs_pred``.
        """
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
                residual_target=self.residual_target,
            )

            actual = val_df[["sales_date", "revenue", "cogs"]].copy()
            actual = actual.rename(columns={"sales_date": "date"})
            merged = actual.merge(pred, on="date", suffixes=("_actual", "_pred"))

            for target in ("revenue", "cogs"):
                y_true = merged[f"{target}_actual"].to_numpy()
                y_pred = merged[f"{target}_pred"].to_numpy()

                mae = float(mean_absolute_error(y_true, y_pred))
                rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
                r2 = float(r2_score(y_true, y_pred)) if np.var(y_true) > 0 else 0.0

                results[target].append({"fold": fold + 1, "mae": mae, "rmse": rmse, "r2": r2})

            if return_predictions:
                fold_preds.append(merged[["date", "revenue_pred", "cogs_pred"]].copy())

        if return_predictions:
            return results, fold_preds
        return results

    def train_final(self, df: pd.DataFrame) -> tuple[BaseForecaster, list[str]]:
        """Train final models on the full historical dataset."""
        df = df.copy().sort_values("sales_date").reset_index(drop=True)
        cols = feature_columns(df)
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
        residual_target: bool = False,
    ) -> None:
        model_dir.mkdir(parents=True, exist_ok=True)

        meta = {
            "model_type": model_type,
            "feature_columns": feature_cols,
            "cogs_column": cogs_column,
            "residual_target": residual_target,
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
    ) -> tuple[BaseForecaster, list[str], str, str, bool]:
        from datathon.modeling.forecasters import get_forecaster

        with open(model_dir / "meta.json") as f:
            meta = json.load(f)

        model_type = meta["model_type"]
        feature_cols = meta["feature_columns"]
        cogs_column = meta.get("cogs_column", "cogs")
        residual_target = meta.get("residual_target", False)

        forecaster_cls = get_forecaster(model_type)
        forecaster = forecaster_cls.load(model_dir / "forecaster.pkl")

        return forecaster, feature_cols, model_type, cogs_column, residual_target
