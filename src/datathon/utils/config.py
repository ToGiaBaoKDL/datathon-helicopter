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


def resolve_targets(config: dict[str, Any]) -> tuple[str, str, bool]:
    """Determine revenue / COGS target columns from modeling config.

    Returns
    -------
    (revenue_column, cogs_column, residual_target)
    """
    cogs_target = config.get("cogs_target", "absolute")
    residual_target = config.get("residual_target", False)

    if cogs_target == "ratio":
        cogs_column = "cogs_ratio"
    elif residual_target:
        cogs_column = "cogs_residual"
    else:
        cogs_column = "cogs"

    revenue_column = "revenue_residual" if residual_target else "revenue"

    if residual_target and cogs_target == "ratio":
        raise ValueError(
            "Invalid config: cogs_target='ratio' + residual_target=True is an anti-pattern. "
            "When residual_target=True, COGS should also be predicted as a residual "
            "(cogs_target='absolute') so that revenue and COGS are independent deviations "
            "from their respective YoY baselines. "
            "Using ratio causes error compounding because cogs = revenue * ratio, "
            "and revenue already contains prediction error from the residual model. "
            "Set cogs_target='absolute' in configs/modeling.yaml."
        )

    return revenue_column, cogs_column, residual_target


def load_tracking_config() -> dict[str, Any]:
    """Load tracking configuration (MLflow on/off, URI, experiment name)."""
    if _TRACKING_CONFIG_PATH.exists():
        return _load_yaml(_TRACKING_CONFIG_PATH)
    return {}
