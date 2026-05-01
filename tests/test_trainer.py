from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from datathon.modeling.cv import ExpandingWindowCV

try:
    from datathon.modeling.forecasters.lightgbm import LightGBMForecaster

    _HAS_LIGHTGBM = True
except ImportError:
    LightGBMForecaster = None  # type: ignore[misc,assignment]
    _HAS_LIGHTGBM = False

try:
    from datathon.modeling.forecasters.xgboost import XGBoostForecaster

    _HAS_XGBOOST = True
except ImportError:
    XGBoostForecaster = None  # type: ignore[misc,assignment]
    _HAS_XGBOOST = False

try:
    from datathon.modeling.forecasters.catboost import CatBoostForecaster

    _HAS_CATBOOST = True
except ImportError:
    CatBoostForecaster = None  # type: ignore[misc,assignment]
    _HAS_CATBOOST = False
from datathon.modeling.recursive import (
    _prepare_future_frame,
    feature_columns,
    recursive_forecast,
)
from datathon.modeling.trainer import Trainer


def _make_synthetic_df(n: int = 30, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2023-01-01", periods=n, freq="D")
    revenue = rng.random(n) * 1_000_000
    cogs = rng.random(n) * 800_000
    df = pd.DataFrame(
        {
            "sales_date": dates,
            "revenue": revenue,
            "cogs": cogs,
            "year": dates.year,
            "month": dates.month,
            "quarter": dates.quarter,
            "day_of_week": dates.dayofweek,
            "is_weekend": (dates.dayofweek >= 5).astype(int),
            "day_of_year": dates.dayofyear,
            "days_to_month_end": 1,
            "days_to_quarter_end": 10,
            "day_of_week_sin": np.sin(2 * np.pi * dates.dayofweek / 7),
            "day_of_week_cos": np.cos(2 * np.pi * dates.dayofweek / 7),
            "day_of_year_sin": np.sin(2 * np.pi * dates.dayofyear / 365),
            "day_of_year_cos": np.cos(2 * np.pi * dates.dayofyear / 365),
            "days_since_2019": (dates - pd.Timestamp("2019-01-01")).days,
            "sessions": rng.integers(100, 1000, size=n),
        }
    )
    # Add lag / rolling placeholders required by recursive forecast
    df["lag_1d_revenue"] = pd.Series(revenue).shift(1)
    df["lag_2d_revenue"] = pd.Series(revenue).shift(2)
    df["lag_3d_revenue"] = pd.Series(revenue).shift(3)
    df["lag_7d_revenue"] = pd.Series(revenue).shift(7)
    df["lag_14d_revenue"] = pd.Series(revenue).shift(14)
    df["lag_28d_revenue"] = pd.Series(revenue).shift(28)
    df["lag_365d_revenue"] = pd.Series(revenue).shift(365)
    df["lag_1d_cogs"] = pd.Series(cogs).shift(1)
    df["lag_7d_cogs"] = pd.Series(cogs).shift(7)
    df["lag_28d_cogs"] = pd.Series(cogs).shift(28)
    df["lag_365d_cogs"] = pd.Series(cogs).shift(365)
    df["revenue_baseline"] = df["lag_365d_revenue"]
    df["cogs_baseline"] = df["lag_365d_cogs"]
    df["revenue_residual"] = df["revenue"] - df["revenue_baseline"]
    df["cogs_residual"] = df["cogs"] - df["cogs_baseline"]

    df["lag_1d_rev_residual"] = df["revenue_residual"].shift(1)
    df["lag_7d_rev_residual"] = df["revenue_residual"].shift(7)
    df["lag_1d_cogs_residual"] = df["cogs_residual"].shift(1)
    df["lag_7d_cogs_residual"] = df["cogs_residual"].shift(7)
    df["lag_1d_rev_wow_growth"] = (
        df["lag_1d_revenue"] / pd.Series(revenue).shift(8).replace(0, np.nan) - 1
    ).fillna(0.0)
    df["lag_1d_rev_mom_growth"] = (
        df["lag_1d_revenue"] / pd.Series(revenue).shift(29).replace(0, np.nan) - 1
    ).fillna(0.0)
    df["lag_1d_rev_yoy_growth"] = (
        df["lag_1d_revenue"] / df["lag_365d_revenue"].replace(0, np.nan) - 1
    ).fillna(0.0)
    df["rev_wow_acceleration"] = df["lag_1d_rev_wow_growth"].diff().fillna(0.0)
    df["rev_mom_acceleration"] = df["lag_1d_rev_mom_growth"].diff().fillna(0.0)
    df["rev_yoy_acceleration"] = df["lag_1d_rev_yoy_growth"].diff().fillna(0.0)
    df["roll_mean_7d_revenue"] = df["lag_1d_revenue"].rolling(window=7, min_periods=1).mean()
    df["roll_mean_28d_revenue"] = df["lag_1d_revenue"].rolling(window=28, min_periods=1).mean()
    df["roll_mean_365d_revenue"] = df["lag_1d_revenue"].rolling(window=365, min_periods=1).mean()
    df["roll_std_7d_revenue"] = df["lag_1d_revenue"].rolling(window=7, min_periods=2).std()
    df["roll_std_28d_revenue"] = df["lag_1d_revenue"].rolling(window=28, min_periods=2).std()
    df["roll_std_365d_revenue"] = df["lag_1d_revenue"].rolling(window=365, min_periods=2).std()
    df["roll_mean_7d_cogs"] = df["lag_1d_cogs"].rolling(window=7, min_periods=1).mean()
    df["roll_mean_28d_cogs"] = df["lag_1d_cogs"].rolling(window=28, min_periods=1).mean()
    df["ema_7d_revenue"] = df["lag_1d_revenue"].ewm(span=7, min_periods=1).mean()
    df["ema_28d_revenue"] = df["lag_1d_revenue"].ewm(span=28, min_periods=1).mean()
    return df


def test_expanding_window_cv_yields_correct_splits() -> None:
    df = _make_synthetic_df(n=100)
    cv = ExpandingWindowCV(n_folds=3, horizon_days=10)
    splits = list(cv.split(df))

    assert len(splits) == 3
    for _fold, train_idx, val_idx in splits:
        assert len(val_idx) == 10
        assert max(train_idx) < min(val_idx)


def test_prepare_future_frame_has_calendar_features() -> None:
    history = _make_synthetic_df(n=10)
    scaffold = pd.DataFrame({"date": pd.date_range("2023-01-11", periods=3, freq="D")})
    future = _prepare_future_frame(history, scaffold)

    assert "month" in future.columns
    assert "day_of_week" in future.columns
    assert len(future) == 3


_FORECASTER_PARAMS: list[tuple] = []
if _HAS_LIGHTGBM:
    _FORECASTER_PARAMS.append((LightGBMForecaster, {"verbose": -1}))
if _HAS_XGBOOST:
    _FORECASTER_PARAMS.append((XGBoostForecaster, {"verbosity": 0}))
if _HAS_CATBOOST:
    _FORECASTER_PARAMS.append((CatBoostForecaster, {"iterations": 10, "verbose": False}))


@pytest.mark.parametrize("forecaster_cls,kwargs", _FORECASTER_PARAMS)
def test_recursive_forecast_produces_non_negative_predictions(forecaster_cls, kwargs) -> None:
    history = _make_synthetic_df(n=60)
    scaffold = pd.DataFrame({"date": pd.date_range("2023-03-02", periods=5, freq="D")})

    forecaster = forecaster_cls(**kwargs)
    trainer = Trainer(forecaster=forecaster, cv=ExpandingWindowCV(n_folds=2, horizon_days=5))
    forecaster_fitted, _ = trainer.train_final(history)

    preds = recursive_forecast(forecaster_fitted, history, scaffold, feature_columns(history))

    assert len(preds) == 5
    assert (preds["revenue"] >= 0).all()
    assert (preds["cogs"] >= 0).all()


@pytest.mark.parametrize("forecaster_cls,kwargs", _FORECASTER_PARAMS)
def test_trainer_cv_runs_without_error(forecaster_cls, kwargs) -> None:
    df = _make_synthetic_df(n=100)
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


@pytest.mark.parametrize("forecaster_cls,kwargs", _FORECASTER_PARAMS)
def test_trainer_cv_returns_predictions_when_asked(forecaster_cls, kwargs) -> None:
    df = _make_synthetic_df(n=100)
    forecaster = forecaster_cls(**kwargs)
    trainer = Trainer(forecaster=forecaster, cv=ExpandingWindowCV(n_folds=2, horizon_days=10))
    results, preds = trainer.run_cv(df, return_predictions=True)

    assert isinstance(preds, list)
    assert len(preds) == 2
    for fold_pred in preds:
        assert list(fold_pred.columns) == ["date", "revenue_pred", "cogs_pred"]
        assert len(fold_pred) == 10


@pytest.mark.parametrize("forecaster_cls,kwargs", _FORECASTER_PARAMS)
def test_trainer_save_and_load_artifacts(forecaster_cls, kwargs, tmp_path) -> None:
    df = _make_synthetic_df(n=50)
    forecaster = forecaster_cls(**kwargs)
    trainer = Trainer(forecaster=forecaster, cv=ExpandingWindowCV(n_folds=2, horizon_days=5))
    forecaster_fitted, feature_cols = trainer.train_final(df)

    model_dir = tmp_path / "models"
    model_type_name = forecaster_cls.__name__.lower().replace("forecaster", "")
    Trainer.save_artifacts(model_dir, forecaster_fitted, feature_cols, model_type=model_type_name)

    loaded_forecaster, loaded_features, loaded_type, _cogs_col, _residual, _seq, _rh = (
        Trainer.load_artifacts(model_dir)
    )
    assert loaded_features == feature_cols
    X = df[feature_cols].iloc[[-1]]
    assert loaded_forecaster.predict(X)[0][0] == pytest.approx(forecaster_fitted.predict(X)[0][0])
