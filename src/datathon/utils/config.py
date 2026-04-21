"""Load centralized configuration files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from datathon.utils.paths import project_root

_DEFAULT_CONFIG_PATH = project_root() / "configs" / "modeling.yaml"


def load_modeling_config(path: Path | None = None) -> dict[str, Any]:
    config_path = path or _DEFAULT_CONFIG_PATH
    with open(config_path) as f:
        return yaml.safe_load(f)
