"""Generic training orchestrator for any BaseForecaster."""

from __future__ import annotations

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
    ):
        self.forecaster = forecaster
        self.cv = cv

    def run_cv(self, df: pd.DataFrame) -> dict[str, list[dict[str, float]]]:
        """Run expanding-window CV and return per-fold metrics."""
        df = df.copy().sort_values("sales_date").reset_index(drop=True)
        cols = feature_columns(df)

        results: dict[str, list[dict[str, float]]] = {"revenue": [], "cogs": []}

        for fold, train_idx, val_idx in self.cv.split(df):
            train_df = df.iloc[train_idx]
            val_df = df.iloc[val_idx]

            self.forecaster.fit(train_df[cols], train_df["revenue"], train_df["cogs"])

            pred = recursive_forecast(
                self.forecaster,
                train_df,
                val_df[["sales_date"]].rename(columns={"sales_date": "date"}),
                cols,
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

        return results

    def train_final(self, df: pd.DataFrame) -> tuple[BaseForecaster, list[str]]:
        """Train final models on the full historical dataset."""
        df = df.copy().sort_values("sales_date").reset_index(drop=True)
        cols = feature_columns(df)
        self.forecaster.fit(df[cols], df["revenue"], df["cogs"])
        return self.forecaster, cols

    @staticmethod
    def save_artifacts(
        model_dir: Path,
        forecaster: BaseForecaster,
        feature_cols: list[str],
        model_type: str,
        cv_results: dict | None = None,
    ) -> None:
        model_dir.mkdir(parents=True, exist_ok=True)

        meta = {"model_type": model_type, "feature_columns": feature_cols}
        with open(model_dir / "meta.json", "w") as f:
            json.dump(meta, f, indent=2)

        forecaster.save(model_dir / "forecaster.pkl")

        if cv_results is not None:
            with open(model_dir / "cv_results.json", "w") as f:
                json.dump(cv_results, f, indent=2)

    @staticmethod
    def load_artifacts(
        model_dir: Path,
    ) -> tuple[BaseForecaster, list[str], str]:
        from datathon.modeling.forecasters import get_forecaster

        with open(model_dir / "meta.json") as f:
            meta = json.load(f)

        model_type = meta["model_type"]
        feature_cols = meta["feature_columns"]

        forecaster_cls = get_forecaster(model_type)
        forecaster = forecaster_cls.load(model_dir / "forecaster.pkl")

        return forecaster, feature_cols, model_type
