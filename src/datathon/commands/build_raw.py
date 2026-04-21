from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias

import yaml
from rich.table import Table

from datathon.commands.common import CommandError, ensure_no_unknown_args, take_flag, take_option
from datathon.utils.console import console
from datathon.utils.duckdb_io import connect
from datathon.utils.paths import ensure_dir, project_root, raw_data_dir, warehouse_path

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
ExpectedColumn: TypeAlias = str | tuple[str, ...]

_EXPECTED_RAW_COLUMNS: dict[str, tuple[ExpectedColumn, ...]] = {
    "sales": (("date", "Date"), ("revenue", "Revenue"), ("cogs", "COGS")),
    "sample_submission": (("date", "Date"), ("revenue", "Revenue"), ("cogs", "COGS")),
    "orders": (
        "order_id",
        "order_date",
        "customer_id",
        "zip",
        "order_status",
        "payment_method",
        "device_type",
        "order_source",
    ),
    "order_items": (
        "order_id",
        "product_id",
        "quantity",
        "unit_price",
        "discount_amount",
        "promo_id",
        "promo_id_2",
    ),
    "products": (
        "product_id",
        "product_name",
        "category",
        "segment",
        "size",
        "color",
        "price",
        "cogs",
    ),
    "customers": (
        "customer_id",
        "zip",
        "city",
        "signup_date",
        "gender",
        "age_group",
        "acquisition_channel",
    ),
    "geography": (
        "zip",
        "city",
        "region",
        "district",
    ),
    "promotions": (
        "promo_id",
        "promo_name",
        "promo_type",
        "discount_value",
        "start_date",
        "end_date",
        "applicable_category",
        "promo_channel",
        "stackable_flag",
        "min_order_value",
    ),
    "payments": (
        "order_id",
        "payment_method",
        "payment_value",
        "installments",
    ),
    "shipments": (
        "order_id",
        "ship_date",
        "delivery_date",
        "shipping_fee",
    ),
    "returns": (
        "return_id",
        "order_id",
        "product_id",
        "return_date",
        "return_reason",
        "return_quantity",
        "refund_amount",
    ),
    "reviews": (
        "review_id",
        "order_id",
        "product_id",
        "customer_id",
        "review_date",
        "rating",
        "review_title",
    ),
    "inventory": (
        "snapshot_date",
        "product_id",
        "stock_on_hand",
        "units_received",
        "units_sold",
        "stockout_days",
        "days_of_supply",
        "fill_rate",
        "stockout_flag",
        "overstock_flag",
        "reorder_flag",
        "sell_through_rate",
        "product_name",
        "category",
        "segment",
        "year",
        "month",
    ),
    "web_traffic": (
        "date",
        "sessions",
        "unique_visitors",
        "page_views",
        "bounce_rate",
        "avg_session_duration_sec",
        "traffic_source",
    ),
}


@dataclass(frozen=True)
class BuildRawOptions:
    config: Path
    input_dir: Path
    warehouse: Path
    strict: bool


def parse_args(raw_args: list[str]) -> BuildRawOptions:
    args = list(raw_args)
    config = Path(
        take_option(args, "--config", default=str(project_root() / "configs" / "raw_tables.yaml"))
    )
    input_dir = Path(take_option(args, "--input-dir", default=str(raw_data_dir())))
    warehouse = Path(take_option(args, "--warehouse", default=str(warehouse_path())))
    strict = take_flag(args, "--strict")
    ensure_no_unknown_args(args)
    return BuildRawOptions(config=config, input_dir=input_dir, warehouse=warehouse, strict=strict)


def print_help() -> None:
    console.print("[bold]build-raw[/bold]")
    console.print(
        "[dim]Usage:[/dim] datathon build-raw [--config <path>] [--input-dir <path>] "
        "[--warehouse <path>] [--strict]"
    )


def run(options: BuildRawOptions) -> None:
    ensure_dir(options.warehouse.parent)
    tables = _load_raw_tables_config(options.config)

    loaded_rows: list[tuple[str, int, str]] = []
    missing_tables: list[str] = []

    with connect(options.warehouse) as connection:
        _create_raw_schema(connection)

        for table in tables:
            table_name = str(table["table_name"])
            candidates = list(table["candidate_files"])

            csv_path = _find_candidate_file(options.input_dir, candidates)
            if csv_path is None:
                missing_tables.append(table_name)
                continue

            _load_csv_to_table(connection, csv_path, table_name)

            expected_columns = _EXPECTED_RAW_COLUMNS.get(table_name)
            if expected_columns:
                _require_columns(connection, table_name, expected_columns)

            row_count = connection.execute(f"SELECT COUNT(*) FROM raw.{table_name}").fetchone()[0]
            loaded_rows.append((table_name, int(row_count), csv_path.name))

    if loaded_rows:
        table = Table(title="Loaded raw tables")
        table.add_column("Table")
        table.add_column("Rows", justify="right")
        table.add_column("Source file")
        for table_name, row_count, file_name in loaded_rows:
            table.add_row(f"raw.{table_name}", f"{row_count}", file_name)
        console.print(table)

    if missing_tables:
        message = f"Missing source files for tables: {', '.join(missing_tables)}"
        if options.strict:
            raise RuntimeError(message)
        console.print(f"[yellow]Warning:[/yellow] {message}")

    console.print(f"Raw warehouse ready at [bold]{options.warehouse}[/bold]")


def _require_columns(
    connection,
    table_name: str,
    expected_columns: Sequence[ExpectedColumn],
) -> None:
    existing_columns = {
        row[1].lower()
        for row in connection.execute(f"PRAGMA table_info('raw.{table_name}')").fetchall()
    }

    missing: list[str] = []
    for expected in expected_columns:
        if isinstance(expected, tuple):
            if all(alias.lower() not in existing_columns for alias in expected):
                missing.append("/".join(expected))
            continue

        if expected.lower() not in existing_columns:
            missing.append(expected)

    if missing:
        missing_list = ", ".join(missing)
        raise RuntimeError(f"raw.{table_name} is missing expected columns: {missing_list}")


def _load_raw_tables_config(config_path: Path) -> list[dict[str, object]]:
    with config_path.open("r", encoding="utf-8") as file:
        parsed = yaml.safe_load(file) or {}

    tables = parsed.get("tables")
    if not isinstance(tables, list):
        raise CommandError("Invalid raw table config: 'tables' must be a list.")

    normalized: list[dict[str, object]] = []
    for table in tables:
        if not isinstance(table, dict):
            raise CommandError("Invalid raw table config: each table must be a mapping.")

        table_name = table.get("table_name")
        candidate_files = table.get("candidate_files")
        if not isinstance(table_name, str) or not _IDENTIFIER_RE.match(table_name):
            raise CommandError(f"Invalid table_name in config: {table_name!r}")
        if not isinstance(candidate_files, list) or not candidate_files:
            raise CommandError(f"Invalid candidate_files for table '{table_name}'.")
        if not all(isinstance(name, str) for name in candidate_files):
            raise CommandError(f"candidate_files for table '{table_name}' must be strings.")

        normalized.append({"table_name": table_name, "candidate_files": candidate_files})

    return normalized


def _find_candidate_file(input_dir: Path, candidates: Sequence[str]) -> Path | None:
    for candidate in candidates:
        candidate_path = input_dir / candidate
        if candidate_path.exists():
            return candidate_path
    return None


def _create_raw_schema(connection) -> None:
    connection.execute("CREATE SCHEMA IF NOT EXISTS raw")


def _load_csv_to_table(connection, csv_path: Path, table_name: str) -> None:
    escaped_path = str(csv_path).replace("'", "''")
    sql = f"""
    CREATE OR REPLACE TABLE raw.{table_name} AS
    SELECT *
    FROM read_csv_auto('{escaped_path}', header=true, sample_size=-1)
    """
    connection.execute(sql)
