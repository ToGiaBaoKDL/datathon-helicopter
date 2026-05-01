"""Factory helpers to instantiate forecasters from config."""

from __future__ import annotations

from typing import Any

from datathon.modeling.forecasters import get_forecaster


def build_forecaster(model_type: str, config: dict[str, Any]) -> Any:
    """Instantiate a forecaster of *model_type* using hyperparameters from *config*.

    *config* is the dict returned by ``load_modeling_config()``.
    """
    model_cfg = config.get("models", {}).get(model_type)
    if model_cfg is None:
        raise ValueError(
            f"Model type '{model_type}' not found in config['models']. "
            f"Available: {list(config.get('models', {}).keys())}"
        )

    if config.get("sequential_cogs", False):
        from datathon.modeling.forecasters.sequential import SequentialForecaster

        return SequentialForecaster(model_type, **model_cfg)

    forecaster_cls = get_forecaster(model_type)
    return forecaster_cls(**model_cfg)
