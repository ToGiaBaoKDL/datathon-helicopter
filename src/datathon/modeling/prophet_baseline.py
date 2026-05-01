"""Prophet baseline computation for trend + seasonality."""

from __future__ import annotations

import logging
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from prophet import Prophet

# Suppress verbose cmdstanpy INFO logs during Prophet fitting
logging.getLogger("cmdstanpy").setLevel(logging.WARNING)


class ProphetBaseline:
    """Fits Prophet models for revenue and COGS."""

    def __init__(self) -> None:
        self.model_rev: Prophet | None = None
        self.model_cogs: Prophet | None = None
        self._log_transform: bool = False

    def fit(self, df: pd.DataFrame, log_transform: bool = False) -> None:
        """Fit Prophet on historical revenue and COGS.

        Parameters
        ----------
        log_transform:
            When True, fit on ``log1p(revenue)`` so the baseline is in log
            space.  Used together with ``target_transform: log_residual``.
        """
        self._log_transform = log_transform
        rev_raw = df["revenue"].clip(lower=0)
        cogs_raw = df["cogs"].clip(lower=0)

        rev_y = np.log1p(rev_raw) if log_transform else rev_raw
        cogs_y = np.log1p(cogs_raw) if log_transform else cogs_raw

        rev_df = pd.DataFrame({"ds": df["sales_date"], "y": rev_y})
        cogs_df = pd.DataFrame({"ds": df["sales_date"], "y": cogs_y})

        self.model_rev = Prophet(yearly_seasonality=True, weekly_seasonality=True)
        self.model_rev.fit(rev_df)

        self.model_cogs = Prophet(yearly_seasonality=True, weekly_seasonality=True)
        self.model_cogs.fit(cogs_df)

    def predict_history(self, df: pd.DataFrame) -> pd.DataFrame:
        """Return in-sample Prophet predictions for historical dates."""
        if self.model_rev is None or self.model_cogs is None:
            raise RuntimeError("ProphetBaseline has not been fitted yet.")

        future_rev = pd.DataFrame({"ds": df["sales_date"]})
        pred_rev = self.model_rev.predict(future_rev)[["ds", "yhat"]]

        future_cogs = pd.DataFrame({"ds": df["sales_date"]})
        pred_cogs = self.model_cogs.predict(future_cogs)[["ds", "yhat"]]

        return pd.DataFrame(
            {
                "sales_date": df["sales_date"].values,
                "prophet_revenue_baseline": pred_rev["yhat"].values,
                "prophet_cogs_baseline": pred_cogs["yhat"].values,
            }
        )

    def predict_future(self, scaffold: pd.DataFrame) -> pd.DataFrame:
        """Return out-of-sample Prophet predictions for forecast dates."""
        if self.model_rev is None or self.model_cogs is None:
            raise RuntimeError("ProphetBaseline has not been fitted yet.")

        dates = pd.to_datetime(scaffold["date"])
        future_rev = pd.DataFrame({"ds": dates})
        pred_rev = self.model_rev.predict(future_rev)[["ds", "yhat"]]

        future_cogs = pd.DataFrame({"ds": dates})
        pred_cogs = self.model_cogs.predict(future_cogs)[["ds", "yhat"]]

        return pd.DataFrame(
            {
                "date": dates.values,
                "prophet_revenue_baseline": pred_rev["yhat"].values,
                "prophet_cogs_baseline": pred_cogs["yhat"].values,
            }
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self, f)

    @classmethod
    def load(cls, path: Path) -> ProphetBaseline:
        with open(path, "rb") as f:
            return pickle.load(f)
