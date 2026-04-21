from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from datathon.commands import (
    baseline,
    build_raw,
    compare_models,
    download_data,
    export_model_data,
    predict,
    submit_kaggle,
    train,
)


@dataclass(frozen=True)
class CommandSpec:
    description: str
    parse_args: Callable[[list[str]], Any]
    run: Callable[[Any], None]
    print_help: Callable[[], None]


COMMANDS: dict[str, CommandSpec] = {
    "download-data": CommandSpec(
        description="Download and extract Kaggle competition files.",
        parse_args=download_data.parse_args,
        run=download_data.run,
        print_help=download_data.print_help,
    ),
    "build-raw": CommandSpec(
        description="Build raw DuckDB tables from CSV files.",
        parse_args=build_raw.parse_args,
        run=build_raw.run,
        print_help=build_raw.print_help,
    ),
    "export-model-data": CommandSpec(
        description="Export modeling mart as Parquet dataset.",
        parse_args=export_model_data.parse_args,
        run=export_model_data.run,
        print_help=export_model_data.print_help,
    ),
    "baseline": CommandSpec(
        description="Evaluate baseline or generate submission.",
        parse_args=baseline.parse_args,
        run=baseline.run,
        print_help=baseline.print_help,
    ),
    "submit-kaggle": CommandSpec(
        description="Submit a CSV file to Kaggle competition.",
        parse_args=submit_kaggle.parse_args,
        run=submit_kaggle.run,
        print_help=submit_kaggle.print_help,
    ),
    "train": CommandSpec(
        description="Train forecasting models and evaluate via expanding-window CV.",
        parse_args=train.parse_args,
        run=train.run,
        print_help=train.print_help,
    ),
    "predict": CommandSpec(
        description="Generate submission predictions from trained models.",
        parse_args=predict.parse_args,
        run=predict.run,
        print_help=predict.print_help,
    ),
    "compare-models": CommandSpec(
        description="Compare all registered models, pick best, train final, and submit.",
        parse_args=compare_models.parse_args,
        run=compare_models.run,
        print_help=compare_models.print_help,
    ),
}
