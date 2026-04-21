from __future__ import annotations

import shutil
import subprocess
import zipfile
from dataclasses import dataclass
from pathlib import Path

from rich.table import Table

from datathon.commands.common import ensure_no_unknown_args, take_flag, take_option
from datathon.utils.competition import default_competition_slug
from datathon.utils.console import console
from datathon.utils.kaggle import (
    ensure_kaggle_cli_and_auth,
    load_kaggle_credentials,
    validate_competition_access,
)
from datathon.utils.paths import ensure_dir, raw_data_dir


@dataclass(frozen=True)
class DownloadOptions:
    competition: str
    output_dir: Path
    force: bool


def parse_args(raw_args: list[str]) -> DownloadOptions:
    args = list(raw_args)
    competition = take_option(args, "--competition", default=default_competition_slug())
    output_dir = Path(take_option(args, "--output-dir", default=str(raw_data_dir())))
    force = take_flag(args, "--force")
    ensure_no_unknown_args(args)
    return DownloadOptions(competition=competition, output_dir=output_dir, force=force)


def print_help() -> None:
    console.print("[bold]download-data[/bold]")
    console.print(
        "[dim]Usage:[/dim] datathon download-data [--competition <slug>] "
        "[--output-dir <path>] [--force]"
    )
    console.print("[dim]Default slug:[/dim] configs/competition.yaml -> competition.kaggle_slug")


def run(options: DownloadOptions) -> None:
    load_kaggle_credentials()
    ensure_kaggle_cli_and_auth()
    ensure_dir(options.output_dir)

    if options.force:
        _clear_directory(options.output_dir)

    _download_competition_files(options.competition, options.output_dir)
    _extract_zip_archives(options.output_dir)
    _cleanup_download_artifacts(options.output_dir)

    csv_count = len(list(options.output_dir.glob("*.csv")))
    table = Table(show_header=False)
    table.add_row("Competition", options.competition)
    table.add_row("Output directory", str(options.output_dir))
    table.add_row("CSV files", str(csv_count))
    console.print(table)


def _clear_directory(directory: Path) -> None:
    if not directory.exists():
        return

    for child in directory.iterdir():
        if child.is_file():
            child.unlink()
        elif child.is_dir():
            shutil.rmtree(child)


def _download_competition_files(competition: str, output_dir: Path) -> None:
    validate_competition_access(competition)

    subprocess.run(
        [
            "kaggle",
            "competitions",
            "download",
            "-c",
            competition,
            "-p",
            str(output_dir),
        ],
        check=True,
    )


def _extract_zip_archives(output_dir: Path) -> None:
    zip_files = sorted(output_dir.glob("*.zip"))
    if not zip_files:
        raise RuntimeError("No zip files found after download.")

    for zip_path in zip_files:
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(output_dir)


def _cleanup_download_artifacts(output_dir: Path) -> None:
    for zip_path in output_dir.glob("*.zip"):
        zip_path.unlink()

    for notebook_path in output_dir.glob("*.ipynb"):
        notebook_path.unlink()
