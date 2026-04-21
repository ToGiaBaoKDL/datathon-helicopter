from __future__ import annotations

from pathlib import Path

import yaml

from datathon.commands.common import CommandError
from datathon.utils.paths import project_root


def competition_config_path() -> Path:
    return project_root() / "configs" / "competition.yaml"


def load_competition_config() -> dict:
    path = competition_config_path()
    if not path.exists():
        raise CommandError("Missing competition config at configs/competition.yaml.")

    with path.open("r", encoding="utf-8") as file:
        parsed = yaml.safe_load(file) or {}

    competition = parsed.get("competition")
    if not isinstance(competition, dict):
        raise CommandError("Invalid configs/competition.yaml: missing 'competition' section.")

    return competition


def default_competition_slug() -> str:
    competition = load_competition_config()
    slug = competition.get("kaggle_slug")
    if not isinstance(slug, str) or not slug.strip():
        raise CommandError(
            "Missing --competition and no competition.kaggle_slug in configs/competition.yaml."
        )
    return slug.strip()


def submission_columns() -> list[str]:
    competition = load_competition_config()
    columns = competition.get("submission_columns")
    if not isinstance(columns, list) or not columns:
        raise CommandError(
            "Invalid configs/competition.yaml: "
            "competition.submission_columns must be a non-empty list."
        )

    if not all(isinstance(column, str) and column.strip() for column in columns):
        raise CommandError(
            "Invalid configs/competition.yaml: "
            "all submission_columns values must be non-empty strings."
        )

    return [column.strip() for column in columns]
