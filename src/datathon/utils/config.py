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
    valid_transforms = ("identity", "residual", "log")
    if target_transform not in valid_transforms:
        raise ValueError(
            f"target_transform must be one of {valid_transforms}. Got: {target_transform!r}"
        )

    cogs_target = config.get("cogs_target", "absolute")
    cogs_is_ratio = cogs_target == "ratio"

    if cogs_is_ratio:
        cogs_column = "cogs_ratio"
    elif target_transform == "residual":
        cogs_column = "cogs_residual"
    elif target_transform == "log":
        cogs_column = "log_cogs"
    else:
        cogs_column = "cogs"

    if target_transform == "residual":
        revenue_column = "revenue_residual"
    elif target_transform == "log":
        revenue_column = "log_revenue"
    else:
        revenue_column = "revenue"

    # Backward compat: residual + ratio is still discouraged
    if target_transform == "residual" and cogs_is_ratio:
        raise ValueError(
            "Invalid config: cogs_target='ratio' + target_transform='residual' is an anti-pattern. "
            "When predicting residual revenue, COGS should also be predicted as a residual "
            "(cogs_target='absolute') so that revenue and COGS are independent deviations "
            "from their respective YoY baselines. "
            "Set cogs_target='absolute' in configs/modeling.yaml."
        )

    return revenue_column, cogs_column, target_transform, cogs_is_ratio


def load_tracking_config() -> dict[str, Any]:
    """Load tracking configuration (MLflow on/off, URI, experiment name)."""
    if _TRACKING_CONFIG_PATH.exists():
        return _load_yaml(_TRACKING_CONFIG_PATH)
    return {}
