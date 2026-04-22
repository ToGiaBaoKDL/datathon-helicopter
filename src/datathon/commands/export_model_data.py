from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rich.table import Table

from datathon.commands.common import ensure_no_unknown_args, take_option
from datathon.utils.console import console
from datathon.utils.duckdb_io import connect
from datathon.utils.paths import ensure_dir, processed_data_dir, warehouse_path


@dataclass(frozen=True)
class ExportModelDataOptions:
    warehouse: Path
    output_path: Path


def parse_args(raw_args: list[str]) -> ExportModelDataOptions:
    args = list(raw_args)
    warehouse = Path(take_option(args, "--warehouse", default=str(warehouse_path())))
    output_path = Path(
        take_option(
            args,
            "--output-path",
            default=str(processed_data_dir() / "mart_forecast_daily_features.parquet"),
        )
    )
    ensure_no_unknown_args(args)
    return ExportModelDataOptions(warehouse=warehouse, output_path=output_path)


def print_help() -> None:
    console.print("[bold]export-model-data[/bold]")
    console.print(
        "[dim]Usage:[/dim] datathon export-model-data [--warehouse <path>] [--output-path <path>]"
    )


def run(options: ExportModelDataOptions) -> None:
    ensure_dir(options.output_path.parent)

    query = """
        select *
        from marts.mart_forecast_daily_features
        order by sales_date
    """

    with connect(options.warehouse) as connection:
        frame = connection.execute(query).fetchdf()

    frame.to_parquet(options.output_path, index=False)

    table = Table(show_header=False)
    table.add_row("Warehouse", str(options.warehouse))
    table.add_row("Output", str(options.output_path))
    table.add_row("Rows", str(len(frame)))
    console.print(table)
