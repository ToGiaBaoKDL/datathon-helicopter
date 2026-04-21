from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from rich.table import Table

from datathon.commands.common import CommandError, ensure_no_unknown_args, take_flag, take_option
from datathon.utils.competition import default_competition_slug, submission_columns
from datathon.utils.console import console
from datathon.utils.kaggle import ensure_kaggle_cli_and_auth, load_kaggle_credentials
from datathon.utils.paths import submissions_dir


@dataclass(frozen=True)
class SubmitKaggleOptions:
    competition: str
    file_path: Path
    message: str
    dry_run: bool


def parse_args(raw_args: list[str]) -> SubmitKaggleOptions:
    args = list(raw_args)
    competition = take_option(args, "--competition", default=default_competition_slug())
    file_path = Path(
        take_option(
            args,
            "--file",
            default=str(submissions_dir() / "submission.csv"),
        )
    )
    message = take_option(args, "--message", default="")
    dry_run = take_flag(args, "--dry-run")
    ensure_no_unknown_args(args)

    if not dry_run and not message:
        raise CommandError("--message is required unless using --dry-run.")

    return SubmitKaggleOptions(
        competition=competition, file_path=file_path, message=message, dry_run=dry_run
    )


def print_help() -> None:
    console.print("[bold]submit-kaggle[/bold]")
    console.print(
        "[dim]Usage:[/dim] datathon submit-kaggle --message <text> "
        "[--competition <slug>] [--file <path>] [--dry-run]"
    )
    console.print("[dim]Default file:[/dim] data/submissions/submission.csv")
    console.print("[dim]Dry run:[/dim] Validates file schema without uploading.")


def run(options: SubmitKaggleOptions) -> None:
    load_kaggle_credentials()
    ensure_kaggle_cli_and_auth()

    if not options.file_path.exists():
        raise CommandError(f"Submission file not found: {options.file_path}")

    _validate_submission_file(options.file_path)

    if options.dry_run:
        table = Table(show_header=False)
        table.add_row("Competition", options.competition)
        table.add_row("File", str(options.file_path))
        table.add_row("Status", "[green]Dry-run validation passed[/green]")
        console.print(table)
        return

    subprocess.run(
        [
            "kaggle",
            "competitions",
            "submit",
            options.competition,
            "--file",
            str(options.file_path),
            "--message",
            options.message,
        ],
        check=True,
    )

    table = Table(show_header=False)
    table.add_row("Competition", options.competition)
    table.add_row("File", str(options.file_path))
    table.add_row("Message", options.message)
    console.print(table)


def _validate_submission_file(file_path: Path) -> None:
    expected_columns = submission_columns()

    try:
        df = pd.read_csv(file_path)
    except Exception as exc:
        raise CommandError(f"Unable to read submission file: {exc}") from exc

    actual_columns = list(df.columns)
    if actual_columns != expected_columns:
        raise CommandError(f"Column mismatch. Expected {expected_columns}, got {actual_columns}.")

    if df.empty:
        raise CommandError("Submission file is empty.")

    null_counts = df.isnull().sum().sum()
    if null_counts:
        console.print(f"[yellow]Warning:[/yellow] {null_counts} null values found in submission.")
