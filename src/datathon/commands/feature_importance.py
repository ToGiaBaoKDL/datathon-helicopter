"""CLI command to analyse feature importance."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rich.table import Table

from datathon.commands.common import CommandError, ensure_no_unknown_args, take_option
from datathon.modeling.factory import build_forecaster
from datathon.modeling.feature_importance import (
    lgb_importance,
    permutation_importance,
    shap_importance,
)
from datathon.modeling.recursive import feature_columns
from datathon.tracking import MlflowTracker
from datathon.utils.config import load_modeling_config, resolve_targets
from datathon.utils.console import console
from datathon.utils.data_loaders import load_training_data
from datathon.utils.help_texts import feature_importance_help
from datathon.utils.paths import warehouse_path


@dataclass(frozen=True)
class FeatureImportanceOptions:
    warehouse: Path
    method: str
    top_n: int
    model_type: str
    config_path: Path | None


def parse_args(raw_args: list[str]) -> FeatureImportanceOptions:
    args = list(raw_args)
    warehouse = Path(take_option(args, "--warehouse", default=str(warehouse_path())))
    method = take_option(args, "--method", default="split")
    top_n = int(take_option(args, "--top-n", default="30"))
    model_type = take_option(args, "--model-type", default="lightgbm")
    config_path_raw = take_option(args, "--config", default="")
    config_path = Path(config_path_raw) if config_path_raw else None

    ensure_no_unknown_args(args)
    valid_methods = ("split", "permutation", "shap", "all")
    if method not in valid_methods:
        raise CommandError(f"--method must be one of: {', '.join(valid_methods)}.")
    return FeatureImportanceOptions(
        warehouse=warehouse,
        method=method,
        top_n=top_n,
        model_type=model_type,
        config_path=config_path,
    )


def print_help() -> None:
    console.print("[bold]feature-importance[/bold]")
    console.print(feature_importance_help())


def run(options: FeatureImportanceOptions) -> None:
    config = load_modeling_config(options.config_path)
    df = load_training_data(config, options.warehouse)
    _, cogs_column, target_transform, _ = resolve_targets(config)

    tracker = MlflowTracker(run_name="feature_importance")
    with tracker:
        if tracker.enabled:
            tracker.log_param("method", options.method)
            tracker.log_param("top_n", options.top_n)
            tracker.log_config(config)

        if options.method in ("split", "all"):
            console.print("\n[bold]LGBM Split Importance (gain)[/bold]")
            result = lgb_importance(df, top_n=options.top_n)
            table = Table(title="Split-Based Feature Importance")
            table.add_column("Feature", style="cyan")
            table.add_column("LGB Gain", justify="right", style="green")
            table.add_column("%", justify="right")
            table.add_column("Tier")
            for _, row in result.iterrows():
                table.add_row(
                    str(row["feature"]),
                    f"{row['lgb_gain']:.1f}",
                    f"{row['lgb_gain_pct']:.2f}%",
                    row["tier"],
                )
            console.print(table)
            console.print("[dim]Tiers: 🟢 >5% | 🟡 1-5% | 🔴 <1%[/dim]\n")

        if options.method in ("permutation", "all"):
            console.print("[bold]Permutation Importance (MAE increase)[/bold]")
            console.print("Running permutation importance (this takes ~30 s)…\n")
            result = permutation_importance(df, top_n=options.top_n)
            table = Table(title="Permutation Feature Importance")
            table.add_column("Feature", style="cyan")
            table.add_column("MAE Δ", justify="right", style="red")
            table.add_column("MAE %", justify="right")
            table.add_column("Std", justify="right", style="dim")
            table.add_column("Tier")
            for _, row in result.iterrows():
                table.add_row(
                    str(row["feature"]),
                    f"{row['perm_importance']:,.0f}",
                    f"{row['perm_importance_pct']:.2f}%",
                    f"±{row['perm_std']:,.0f}",
                    row["tier"],
                )
            console.print(table)
            console.print("[dim]Tiers: 🟢 >5% | 🟡 1-5% | 🔴 <1%[/dim]\n")

        if options.method in ("shap", "all"):
            console.print("[bold]SHAP Importance[/bold]")
            console.print(
                f"Loading and fitting a temporary {options.model_type} model for SHAP analysis…\n"
            )
            forecaster = build_forecaster(options.model_type, config)
            cols = feature_columns(df)
            X = df[cols].fillna(0)
            if target_transform == "log":
                y_rev = df["log_revenue"]
                y_cogs = df["log_cogs"]
            elif target_transform == "residual":
                y_rev = df["revenue_residual"]
                y_cogs = df["cogs_residual"]
            else:
                y_rev = df["revenue"]
                y_cogs = df["cogs"]
            forecaster.model_rev.fit(X, y_rev)
            forecaster.model_cogs.fit(X, y_cogs)

            result = shap_importance(forecaster, df, sample_size=500, top_n=options.top_n)
            table = Table(title="SHAP Mean |Value| Importance")
            table.add_column("Feature", style="cyan")
            table.add_column("SHAP Rev", justify="right", style="green")
            table.add_column("SHAP COGS", justify="right", style="yellow")
            table.add_column("Avg", justify="right")
            table.add_column("%", justify="right")
            table.add_column("Tier")
            for _, row in result.iterrows():
                table.add_row(
                    str(row["feature"]),
                    f"{row['shap_revenue']:.4f}",
                    f"{row['shap_cogs']:.4f}",
                    f"{row['shap_avg']:.4f}",
                    f"{row['shap_pct']:.2f}%",
                    row["tier"],
                )
            console.print(table)
            console.print("[dim]Tiers: 🟢 >5% | 🟡 1-5% | 🔴 <1%[/dim]\n")

        if tracker.enabled:
            tracker.set_tag("status", "analysed")
