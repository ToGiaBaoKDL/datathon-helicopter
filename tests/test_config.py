from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from datathon.utils.config import load_modeling_config, resolve_targets


def test_load_modeling_config_returns_dict() -> None:
    cfg = load_modeling_config()
    assert isinstance(cfg, dict)
    assert "models" in cfg


def test_load_modeling_config_with_overlay(tmp_path: Path) -> None:
    overlay = {"models": {"lightgbm": {"learning_rate": 0.99}}}
    overlay_path = tmp_path / "overlay.yaml"
    overlay_path.write_text(yaml.dump(overlay))

    cfg = load_modeling_config(overlay_path)
    assert cfg["models"]["lightgbm"]["learning_rate"] == 0.99


def test_resolve_targets_identity() -> None:
    cfg = {"cogs_target": "absolute", "target_transform": "identity"}
    rev_col, cogs_col, transform, cogs_is_ratio = resolve_targets(cfg)
    assert rev_col == "revenue"
    assert cogs_col == "cogs"
    assert transform == "identity"
    assert cogs_is_ratio is False


def test_resolve_targets_ratio() -> None:
    cfg = {"cogs_target": "ratio", "target_transform": "identity"}
    rev_col, cogs_col, transform, cogs_is_ratio = resolve_targets(cfg)
    assert rev_col == "revenue"
    assert cogs_col == "cogs_ratio"
    assert transform == "identity"
    assert cogs_is_ratio is True


def test_resolve_targets_residual() -> None:
    cfg = {"cogs_target": "absolute", "target_transform": "residual"}
    rev_col, cogs_col, transform, cogs_is_ratio = resolve_targets(cfg)
    assert rev_col == "revenue_residual"
    assert cogs_col == "cogs_residual"
    assert transform == "residual"
    assert cogs_is_ratio is False


def test_resolve_targets_log() -> None:
    cfg = {"cogs_target": "absolute", "target_transform": "log"}
    rev_col, cogs_col, transform, cogs_is_ratio = resolve_targets(cfg)
    assert rev_col == "log_revenue"
    assert cogs_col == "log_cogs"
    assert transform == "log"
    assert cogs_is_ratio is False


def test_resolve_targets_ratio_plus_residual_raises() -> None:
    """cogs_target='ratio' + target_transform='residual' is an anti-pattern and should raise."""
    cfg = {"cogs_target": "ratio", "target_transform": "residual"}
    with pytest.raises(ValueError):
        resolve_targets(cfg)


def test_resolve_targets_invalid_transform_raises() -> None:
    cfg = {"target_transform": "unknown"}
    with pytest.raises(ValueError, match="target_transform must be one of"):
        resolve_targets(cfg)
