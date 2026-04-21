"""CLI command for seasonal-naive baseline evaluation and submission."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from rich.table import Table

from datathon.commands.common import CommandError, ensure_no_unknown_args, take_option
from datathon.modeling.baselines import compute_metrics, seasonal_naive
from datathon.utils.competition import submission_columns
from datathon.utils.console import console
from datathon.utils.data_loaders import load_forecast_base, load_scaffold
from datathon.utils.paths import submissions_dir, warehouse_path


@dataclass(frozen=True)
class BaselineOptions:
    mode: str
    warehouse: Path
    seasonal_period: int
    output_path: Path | None


def parse_args(raw_args: list[str]) -> BaselineOptions:
    args = list(raw_args)
    mode = take_option(args, "--mode", required=True)
    if mode not in {"evaluate", "submit"}:
        raise CommandError("--mode must be one of: evaluate, submit.")

    seasonal_period_raw = take_option(args, "--seasonal-period", default="7")
    try:
        seasonal_period = int(seasonal_period_raw)
    except ValueError as exc:
        raise CommandError("--seasonal-period must be an integer.") from exc

    if seasonal_period <= 0:
        raise CommandError("--seasonal-period must be > 0.")

    warehouse = Path(take_option(args, "--warehouse", default=str(warehouse_path())))

    output_path: Path | None = None
    if "--output-path" in args:
        if mode == "evaluate":
            raise CommandError("--output-path is only valid with --mode submit.")
        output_path = Path(take_option(args, "--output-path"))
    elif mode == "submit":
        output_path = Path(
            take_option(
                args,
                "--output-path",
                default=str(submissions_dir() / "submission.csv"),
            )
        )

    ensure_no_unknown_args(args)
    return BaselineOptions(
        mode=mode,
        warehouse=warehouse,
        seasonal_period=seasonal_period,
        output_path=output_path,
    )


def print_help() -> None:
    console.print("[bold]baseline[/bold]")
    console.print(
        "[dim]Usage:[/dim] datathon baseline --mode <evaluate|submit> "
        "[--warehouse <path>] [--seasonal-period <int>] [--output-path <path>]"
    )
    console.print("[dim]Note:[/dim] --output-path is only used with --mode submit.")


def _evaluate_baseline(frame: pd.DataFrame, seasonal_period: int) -> None:
    if len(frame) < 2:
        raise RuntimeError("Not enough rows to evaluate baseline.")

    frame = frame.copy()
    frame["sales_date"] = pd.to_datetime(frame["sales_date"])

    split_idx = int(len(frame) * 0.8)
    split_idx = max(1, split_idx)
    split_idx = min(split_idx, len(frame) - 1)

    train = frame.iloc[:split_idx]
    holdout = frame.iloc[split_idx:]

    revenue_pred = seasonal_naive(
        train_series=train["revenue"],
        horizon=len(holdout),
        seasonal_period=seasonal_period,
    )
    cogs_pred = seasonal_naive(
        train_series=train["cogs"],
        horizon=len(holdout),
        seasonal_period=seasonal_period,
    )

    revenue_metrics = compute_metrics(holdout["revenue"].to_numpy(), revenue_pred)
    cogs_metrics = compute_metrics(holdout["cogs"].to_numpy(), cogs_pred)

    metrics_table = Table(title="Baseline evaluation metrics")
    metrics_table.add_column("Target")
    metrics_table.add_column("MAE", justify="right")
    metrics_table.add_column("RMSE", justify="right")
    metrics_table.add_column("R2", justify="right")
    metrics_table.add_row(
        "Revenue",
        f"{revenue_metrics['mae']:.4f}",
        f"{revenue_metrics['rmse']:.4f}",
        f"{revenue_metrics['r2']:.4f}",
    )
    metrics_table.add_row(
        "COGS",
        f"{cogs_metrics['mae']:.4f}",
        f"{cogs_metrics['rmse']:.4f}",
        f"{cogs_metrics['r2']:.4f}",
    )
    console.print(metrics_table)


def _generate_submission(warehouse: Path, seasonal_period: int, output_path: Path) -> Path:
    base = load_forecast_base(warehouse)
    scaffold = load_scaffold(warehouse)

    revenue_forecast = seasonal_naive(
        train_series=base["revenue"],
        horizon=len(scaffold),
        seasonal_period=seasonal_period,
    )
    cogs_forecast = seasonal_naive(
        train_series=base["cogs"],
        horizon=len(scaffold),
        seasonal_period=seasonal_period,
    )

    submission = scaffold.copy()
    submission["revenue"] = revenue_forecast
    submission["cogs"] = cogs_forecast

    expected = submission_columns()
    rename_map = {c.lower(): c for c in expected}
    submission = submission.rename(columns=rename_map)
    submission = submission[expected]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    submission.to_csv(output_path, index=False)
    return output_path


def run(options: BaselineOptions) -> None:
    if options.mode == "evaluate":
        frame = load_forecast_base(options.warehouse)
        _evaluate_baseline(frame, options.seasonal_period)
        return

    if options.output_path is None:
        raise CommandError("--output-path is required for submit mode.")

    output_path = _generate_submission(
        options.warehouse,
        options.seasonal_period,
        options.output_path,
    )
    console.print(f"Submission generated at [bold]{output_path}[/bold]")
