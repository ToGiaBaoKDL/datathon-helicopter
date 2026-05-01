"""Forecasters registry — plug-in entry point for model types."""

from __future__ import annotations

from datathon.modeling.forecasters.base import BaseForecaster

FORECASTERS: dict[str, type[BaseForecaster]] = {}

try:
    from datathon.modeling.forecasters.lightgbm import LightGBMForecaster

    FORECASTERS["lightgbm"] = LightGBMForecaster
except ImportError:
    pass

try:
    from datathon.modeling.forecasters.xgboost import XGBoostForecaster

    FORECASTERS["xgboost"] = XGBoostForecaster
except ImportError:
    pass

try:
    from datathon.modeling.forecasters.catboost import CatBoostForecaster

    FORECASTERS["catboost"] = CatBoostForecaster
except ImportError:
    pass


def list_forecasters() -> list[str]:
    return list(FORECASTERS.keys())


def get_forecaster(model_type: str) -> type[BaseForecaster]:
    if model_type not in FORECASTERS:
        raise ValueError(
            f"Unknown model type '{model_type}'. Available: {', '.join(list_forecasters())}"
        )
    return FORECASTERS[model_type]
