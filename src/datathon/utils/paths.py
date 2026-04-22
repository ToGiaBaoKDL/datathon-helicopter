from __future__ import annotations

from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def raw_data_dir() -> Path:
    return project_root() / "data" / "raw"


def processed_data_dir() -> Path:
    return project_root() / "data" / "processed"


def warehouse_path() -> Path:
    return project_root() / "warehouse" / "datathon.duckdb"


def submissions_dir() -> Path:
    return project_root() / "data" / "submissions"


def models_dir() -> Path:
    return project_root() / "models"


def reports_dir() -> Path:
    return project_root() / "reports"


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
