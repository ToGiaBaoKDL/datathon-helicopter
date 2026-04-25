"""Rich console report generator for audit results."""

from __future__ import annotations

from rich.console import Console

console = Console()


def _section(title: str) -> None:
    console.print(f"\n[bold underline]{title}[/bold underline]")


def generate_report(
    schema: dict,
    nulls: dict,
    row_counts: dict,
    date_gaps: dict | None,
    targets: dict,
    correlations: dict,
    importance: dict,
    autocorrs: dict,
    validation: dict,
) -> None:
    """Render a complete audit report to the console."""

    _section("Mart Schema")
    console.print(f"Rows: {schema['row_count']:,} | Columns: {schema['column_count']}")
    console.print(
        f"Date range: {schema['date_range'][0].date()} → {schema['date_range'][1].date()}"
    )

    _section("Row Counts")
    for mart, cnt in row_counts.items():
        console.print(f"  {mart}: {cnt:,}")

    _section("Null Ratios (top 10)")
    for col, ratio in list(nulls.items())[:10]:
        console.print(f"  {col}: {ratio:.2%}")

    _section("Date Gaps")
    if date_gaps is None:
        console.print("  No gaps found.")
    else:
        console.print(f"  {len(date_gaps)} gap(s) detected.")
        for _, row in date_gaps.iterrows():
            console.print(f"    {row['sales_date'].date()}: +{int(row['gap_days'])} days")

    _section("Target Stats")
    ratio = targets.pop("residual_std_over_revenue_std", None)
    for name, stats in targets.items():
        console.print(f"  {name}: mean={stats['mean']:,.0f}, std={stats['std']:,.0f}")
    if ratio is not None:
        console.print(f"  residual_std / revenue_std = {ratio:.3f}")

    _section("Top Features by |Correlation| with revenue_residual")
    for feat, corr in correlations.get("revenue_residual", {}).head(10).items():
        console.print(f"  {feat}: {corr:.3f}")

    _section("Quick LightGBM Importance (revenue_residual)")
    for feat, imp in importance.get("revenue_residual", {}).head(10).items():
        console.print(f"  {feat}: {imp}")

    _section("Autocorrelations")
    for col, lags in autocorrs.items():
        line = " | ".join(f"lag-{lag}: {val:.3f}" for lag, val in lags.items())
        console.print(f"  {col}: {line}")

    _section("Mart ↔ Recursive Validation")
    if validation["is_valid"]:
        console.print("  [green]All columns classified correctly.[/green]")
    else:
        if validation["unclassified"]:
            console.print(f"  [red]Unclassified:[/red] {validation['unclassified']}")
        if validation["missing_calendar"]:
            console.print(f"  [red]Missing calendar:[/red] {validation['missing_calendar']}")
        if validation["missing_target_derived"]:
            console.print(
                f"  [red]Missing target-derived:[/red] {validation['missing_target_derived']}"
            )
        if validation["missing_meta"]:
            console.print(f"  [red]Missing meta:[/red] {validation['missing_meta']}")
