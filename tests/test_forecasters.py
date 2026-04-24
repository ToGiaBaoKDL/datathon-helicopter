from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from datathon.modeling.factory import build_forecaster
from datathon.modeling.forecasters import FORECASTERS, get_forecaster, list_forecasters
from datathon.modeling.forecasters.base import BaseForecaster
from datathon.modeling.forecasters.lightgbm import LightGBMForecaster


def test_list_forecasters_returns_all_keys() -> None:
    keys = list_forecasters()
    assert set(keys) == {"lightgbm", "xgboost", "catboost"}


def test_get_forecaster_valid() -> None:
    cls = get_forecaster("lightgbm")
    assert cls is LightGBMForecaster


def test_get_forecaster_unknown_raises() -> None:
    with pytest.raises(ValueError, match="Unknown model type"):
        get_forecaster("notamodel")


def test_forecasters_registry_is_dict() -> None:
    assert isinstance(FORECASTERS, dict)
    for name, cls in FORECASTERS.items():
        assert issubclass(cls, BaseForecaster)


def test_build_forecaster_from_config() -> None:
    config = {
        "models": {
            "lightgbm": {"n_estimators": 10, "verbose": -1},
        }
    }
    forecaster = build_forecaster("lightgbm", config)
    assert isinstance(forecaster, LightGBMForecaster)


def test_build_forecaster_missing_model_raises() -> None:
    config = {"models": {}}
    with pytest.raises(ValueError, match="not found in config"):
        build_forecaster("lightgbm", config)


def test_predict_before_fit_raises() -> None:
    forecaster = LightGBMForecaster(verbose=-1)
    X = pd.DataFrame({"a": [1.0]})
    with pytest.raises(RuntimeError, match="not been fitted"):
        forecaster.predict(X)


def test_base_forecaster_best_iterations_default() -> None:
    """best_iterations should return (None, None) by default."""

    class DummyForecaster(BaseForecaster):
        def fit(self, X, y_rev, y_cogs, eval_set=None):
            pass

        def predict(self, X):
            return np.array([1.0]), np.array([0.8])

        def save(self, path):
            pass

        @classmethod
        def load(cls, path):
            return cls()

    f = DummyForecaster()
    assert f.best_iterations() == (None, None)
