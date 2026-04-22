from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from datathon.modeling.cv import ExpandingWindowCV
from datathon.modeling.forecasters.lightgbm import LightGBMForecaster
from datathon.modeling.forecasters.xgboost import XGBoostForecaster
from datathon.modeling.recursive import (
    _prepare_future_frame,
    _recompute_target_features,
    feature_columns,
    recursive_forecast,
)
from datathon.modeling.trainer import Trainer


def _make_synthetic_df(n: int = 30, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2023-01-01", periods=n, freq="D")
    return pd.DataFrame(
        {
            "sales_date": dates,
            "revenue": rng.random(n) * 1_000_000,
            "cogs": rng.random(n) * 800_000,
            "year": dates.year,
            "month": dates.month,
            "quarter": dates.quarter,
            "day_of_week": dates.dayofweek,
            "is_weekend": (dates.dayofweek >= 5).astype(int),
            "day_of_month": dates.day,
            "days_to_month_end": 1,
            "is_month_start": 0,
            "is_month_end": 0,
            "month_sin": np.sin(2 * np.pi * dates.month / 12),
            "month_cos": np.cos(2 * np.pi * dates.month / 12),
            "day_of_week_sin": np.sin(2 * np.pi * dates.dayofweek / 7),
            "day_of_week_cos": np.cos(2 * np.pi * dates.dayofweek / 7),
            "tet_date": pd.Timestamp("2023-01-22"),
            "days_to_tet": (pd.Timestamp("2023-01-22") - dates).days,
            "is_pre_tet_rush": 0,
            "is_tet_holiday": 0,
            "is_post_tet": 0,
            "sessions": rng.integers(100, 1000, size=n),
        }
    )


def test_expanding_window_cv_yields_correct_splits() -> None:
    df = _make_synthetic_df(n=100)
    cv = ExpandingWindowCV(n_folds=3, horizon_days=10)
    splits = list(cv.split(df))

    assert len(splits) == 3
    for _fold, train_idx, val_idx in splits:
        assert len(val_idx) == 10
        assert max(train_idx) < min(val_idx)


def test_recompute_target_features_populates_lags() -> None:
    df = _make_synthetic_df(n=10)
    df["lag_1d_revenue"] = np.nan
    result = _recompute_target_features(df)

    assert pd.isna(result.loc[0, "lag_1d_revenue"])
    assert result.loc[1, "lag_1d_revenue"] == df.loc[0, "revenue"]


def test_prepare_future_frame_has_calendar_features() -> None:
    history = _make_synthetic_df(n=10)
    scaffold = pd.DataFrame({"date": pd.date_range("2023-01-11", periods=3, freq="D")})
    future = _prepare_future_frame(history, scaffold)

    assert "year" in future.columns
    assert "month" in future.columns
    assert future["year"].iloc[0] == 2023
    assert len(future) == 3


@pytest.mark.parametrize(
    "forecaster_cls,kwargs",
    [
        (LightGBMForecaster, {"verbose": -1}),
        (XGBoostForecaster, {"verbosity": 0}),
    ],
)
def test_recursive_forecast_produces_non_negative_predictions(forecaster_cls, kwargs) -> None:
    history = _make_synthetic_df(n=60)
    history = _recompute_target_features(history)
    scaffold = pd.DataFrame({"date": pd.date_range("2023-03-02", periods=5, freq="D")})

    forecaster = forecaster_cls(**kwargs)
    trainer = Trainer(forecaster=forecaster, cv=ExpandingWindowCV(n_folds=2, horizon_days=5))
    forecaster_fitted, _ = trainer.train_final(history)

    preds = recursive_forecast(forecaster_fitted, history, scaffold, feature_columns(history))

    assert len(preds) == 5
    assert (preds["revenue"] >= 0).all()
    assert (preds["cogs"] >= 0).all()


@pytest.mark.parametrize(
    "forecaster_cls,kwargs",
    [
        (LightGBMForecaster, {"verbose": -1}),
        (XGBoostForecaster, {"verbosity": 0}),
    ],
)
def test_trainer_cv_runs_without_error(forecaster_cls, kwargs) -> None:
    df = _make_synthetic_df(n=100)
    df = _recompute_target_features(df)
    forecaster = forecaster_cls(**kwargs)
    trainer = Trainer(forecaster=forecaster, cv=ExpandingWindowCV(n_folds=2, horizon_days=10))
    results = trainer.run_cv(df)

    assert "revenue" in results
    assert "cogs" in results
    assert len(results["revenue"]) == 2
    for fold_res in results["revenue"]:
        assert "mae" in fold_res
        assert "rmse" in fold_res
        assert fold_res["mae"] >= 0


@pytest.mark.parametrize(
    "forecaster_cls,kwargs",
    [
        (LightGBMForecaster, {"verbose": -1}),
        (XGBoostForecaster, {"verbosity": 0}),
    ],
)
def test_trainer_save_and_load_artifacts(forecaster_cls, kwargs, tmp_path) -> None:
    df = _make_synthetic_df(n=50)
    df = _recompute_target_features(df)
    forecaster = forecaster_cls(**kwargs)
    trainer = Trainer(forecaster=forecaster, cv=ExpandingWindowCV(n_folds=2, horizon_days=5))
    forecaster_fitted, feature_cols = trainer.train_final(df)

    model_dir = tmp_path / "models"
    model_type_name = forecaster_cls.__name__.lower().replace("forecaster", "")
    Trainer.save_artifacts(model_dir, forecaster_fitted, feature_cols, model_type=model_type_name)

    loaded_forecaster, loaded_features, loaded_type = Trainer.load_artifacts(model_dir)
    assert loaded_features == feature_cols
    X = df[feature_cols].iloc[[-1]]
    assert loaded_forecaster.predict(X)[0][0] == pytest.approx(forecaster_fitted.predict(X)[0][0])
