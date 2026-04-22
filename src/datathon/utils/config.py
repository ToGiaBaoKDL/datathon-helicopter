"""Load centralized configuration files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from datathon.utils.paths import project_root

_DEFAULT_CONFIG_PATH = project_root() / "configs" / "modeling.yaml"


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
    """Load base modeling config and optionally overlay a delta config.

    *path* can be a full replacement config or a delta (e.g. tuned params
    for a single model).  Delta configs use the same schema as the base
    config; the ``models`` subtree is merged model-by-model.
    """
    config = _load_yaml(_DEFAULT_CONFIG_PATH)
    if path is not None:
        overlay = _load_yaml(path)
        _deep_merge(config, overlay)
    return config
