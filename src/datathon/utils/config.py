"""Load centralized configuration files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from datathon.utils.paths import project_root

_DEFAULT_CONFIG_PATH = project_root() / "configs" / "modeling.yaml"
_TRACKING_CONFIG_PATH = project_root() / "configs" / "tracking.yaml"


def _load_yaml(path: Path) -> dict[str, Any]:
    with open(path) as f:
        return yaml.safe_load(f) or {}


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> None:
    """Recursively merge *overlay* into *base* (mutating *base*)."""
    for key, val in overlay.items():
        if isinstance(val, dict) and key in base and isinstance(base[key], dict):
            _deep_merge(base[key], val)
        else:
            base[key] = val


def load_modeling_config(path: Path | None = None) -> dict[str, Any]:
    """Load base modeling config and optionally overlay a delta config."""
    config = _load_yaml(_DEFAULT_CONFIG_PATH)
    if path is not None:
        overlay = _load_yaml(path)
        _deep_merge(config, overlay)
    return config


def resolve_targets(config: dict[str, Any]) -> tuple[str, str, str, bool]:
    """Determine revenue / COGS target columns and transform mode."""
    target_transform = config.get("target_transform", "identity")
    valid_transforms = ("identity", "residual", "log", "log_residual")
    if target_transform not in valid_transforms:
        raise ValueError(
            f"target_transform must be one of {valid_transforms}. Got: {target_transform!r}"
        )

    if target_transform == "log_residual" and not config.get("prophet_baseline", False):
        raise ValueError(
            "target_transform='log_residual' requires prophet_baseline=true. "
            "The log-space baseline is only provided by Prophet."
        )

    cogs_target = config.get("cogs_target", "absolute")
    cogs_is_ratio = cogs_target == "ratio"

    if cogs_is_ratio:
        cogs_column = "cogs_ratio"
    elif target_transform in ("residual", "log_residual"):
        cogs_column = "cogs_residual"
    elif target_transform == "log":
        cogs_column = "log_cogs"
    else:
        cogs_column = "cogs"

    if target_transform in ("residual", "log_residual"):
        revenue_column = "revenue_residual"
    elif target_transform == "log":
        revenue_column = "log_revenue"
    else:
        revenue_column = "revenue"

    sequential_cogs = config.get("sequential_cogs", False)
    if sequential_cogs and cogs_is_ratio:
        import warnings

        warnings.warn(
            "Anti-pattern detected: sequential_cogs=true with cogs_target='ratio'. "
            "SequentialForecaster feeds predicted_revenue into the COGS model, "
            "but ratio mode reconstructs COGS = revenue * ratio. This creates "
            "redundant information and can hurt performance. "
            "Recommended: set cogs_target='absolute' when sequential_cogs=true.",
            stacklevel=3,
        )

    return revenue_column, cogs_column, target_transform, cogs_is_ratio


def merge_model_config(base_config: dict[str, Any], model_type: str) -> dict[str, Any]:
    """Return a copy of *base_config* with per-model tuned params overlaid.

    Looks for ``configs/tuned/{model_type}.yaml`` and deep-merges it.
    If the file does not exist, returns ``base_config`` unchanged.
    """
    from datathon.utils.paths import configs_dir

    tuned_path = configs_dir() / "tuned" / f"{model_type}.yaml"
    if not tuned_path.exists():
        return dict(base_config)

    merged = dict(base_config)
    overlay = _load_yaml(tuned_path)
    _deep_merge(merged, overlay)
    return merged


def load_tracking_config() -> dict[str, Any]:
    """Load tracking configuration (MLflow on/off, URI, experiment name)."""
    if _TRACKING_CONFIG_PATH.exists():
        return _load_yaml(_TRACKING_CONFIG_PATH)
    return {}
