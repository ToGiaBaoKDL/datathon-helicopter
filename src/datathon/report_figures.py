"""Generate publication-quality figures for NeurIPS report.

Queries DuckDB warehouse and outputs vector PDFs.
Usage:
    uv run python -m src.datathon.report_figures
"""

from __future__ import annotations

import os
from pathlib import Path

import duckdb
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

# ── paths ─────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[2]
WAREHOUSE = REPO_ROOT / "warehouse" / "datathon.duckdb"
OUTPUT_DIR = REPO_ROOT / "reports" / "neurips" / "figures"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── matplotlib style (NeurIPS-compatible) ─────────────────────────
plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["DejaVu Sans"],
        "font.size": 10,
        "axes.labelsize": 10,
        "axes.titlesize": 12,
        "legend.fontsize": 9,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "figure.dpi": 300,
        "savefig.dpi": 300,
        "savefig.format": "pdf",
        "axes.grid": True,
        "grid.alpha": 0.3,
        "grid.linestyle": "--",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.constrained_layout.use": True,
    }
)

# Colour palette (colour-blind safe, print-friendly)
C_PRIMARY = "#1f4e79"  # dark blue
C_SECONDARY = "#c55a11"  # orange
C_TERTIARY = "#548235"  # green
C_QUATERNARY = "#7030a0"  # purple
C_ALERT = "#c00000"  # red
C_REF = "#7f7f7f"  # grey


def _con():
    return duckdb.connect(str(WAREHOUSE), read_only=True)


def save(fig: plt.Figure, name: str) -> None:
    path = OUTPUT_DIR / f"{name}.pdf"
    try:
        fig.tight_layout(pad=0.4)
    except Exception:
        pass
    fig.savefig(path, bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)
    print(f"  saved {path.name}")


# ═══════════════════════════════════════════════════════════════════
#  COMBINED FIGURES (each = 2 charts in 1 figure)
# ═══════════════════════════════════════════════════════════════════


def fig01_revenue_cogs_profit() -> None:
    """F1: Revenue, COGS, Gross Profit area chart."""
    df = (
        _con()
        .execute(
            """
        select sales_date, revenue, cogs, gross_profit
        from marts.mart_daily_executive_kpis
        order by sales_date
        """
        )
        .fetchdf()
    )
    df["sales_date"] = pd.to_datetime(df["sales_date"])

    fig, ax = plt.subplots(figsize=(12, 4.5))
    ax.fill_between(
        df["sales_date"], 0, df["revenue"], color=C_PRIMARY, alpha=0.15, label="Revenue"
    )
    ax.fill_between(df["sales_date"], 0, df["cogs"], color=C_SECONDARY, alpha=0.20, label="COGS")
    ax.plot(df["sales_date"], df["revenue"], color=C_PRIMARY, lw=1.0)
    ax.plot(df["sales_date"], df["cogs"], color=C_SECONDARY, lw=1.0)
    ax.plot(df["sales_date"], df["gross_profit"], color=C_TERTIARY, lw=1.2, label="Gross Profit")

    ax.axvline(pd.Timestamp("2019-01-01"), color=C_ALERT, ls="--", lw=0.8, alpha=0.7)
    ax.text(
        pd.Timestamp("2019-03-01"), ax.get_ylim()[1] * 0.85, "2019 Cliff", color=C_ALERT, fontsize=8
    )

    ax.set_title("Daily Revenue, COGS, and Gross Profit (2012–2022)")
    ax.set_ylabel("VND")
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.legend(loc="upper right", frameon=False)
    save(fig, "fig01_revenue_cogs_profit")


def fig02_demand_capture() -> None:
    """F2: Sessions/Orders (left) + Device Conversion (right)."""
    df_sess = (
        _con()
        .execute(
            """
        select date_part('year', sales_date)::int as year,
               round(avg(sessions), 0) as avg_sessions,
               round(avg(order_count), 0) as avg_orders
        from marts.mart_daily_executive_kpis
        where sessions > 0
        group by 1
        order by 1
        """
        )
        .fetchdf()
    )
    df_dev = (
        _con()
        .execute(
            """
        select breakdown_value as device,
               round(avg(approx_conversion_rate), 4) as rate
        from marts.mart_daily_conversion_breakdown
        where breakdown_type = 'device_type'
        group by 1
        order by rate desc
        """
        )
        .fetchdf()
    )

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), gridspec_kw={"wspace": 0.35})
    # Left: sessions vs orders
    x = np.arange(len(df_sess))
    width = 0.35
    bars = ax1.bar(x - width / 2, df_sess["avg_orders"], width, color=C_PRIMARY, label="Orders")
    ax1.set_ylabel("Daily Orders", color=C_PRIMARY)
    ax1.tick_params(axis="y", labelcolor=C_PRIMARY)
    ax3 = ax1.twinx()
    ax3.plot(
        x, df_sess["avg_sessions"], color=C_SECONDARY, marker="o", ms=3, lw=1.2, label="Sessions"
    )
    ax3.set_ylabel("Daily Sessions", color=C_SECONDARY)
    ax3.tick_params(axis="y", labelcolor=C_SECONDARY)
    ax1.set_xticks(x)
    ax1.set_xticklabels(df_sess["year"], rotation=45, ha="right")
    ax1.set_title("Sessions Rose, Orders Fell — The Conversion Gap")
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax3.get_legend_handles_labels()
    ax1.legend(
        lines1 + lines2,
        labels1 + labels2,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.18),
        frameon=False,
        ncol=2,
        fontsize=8,
    )

    # Right: device conversion
    colours = [C_PRIMARY, C_SECONDARY, C_TERTIARY]
    bars2 = ax2.barh(df_dev["device"], df_dev["rate"] * 100, color=colours)
    ax2.axvline(0.5, color=C_ALERT, ls="--", lw=0.8, alpha=0.7)
    ax2.text(0.52, 1.8, "0.5% target", color=C_ALERT, fontsize=8)
    ax2.set_xlabel("Conversion Rate (%)")
    ax2.set_title("Conversion by Device — Tablet Is the Hidden Leak")
    ax2.invert_yaxis()
    for bar, val in zip(bars2, df_dev["rate"]):
        ax2.text(
            bar.get_width() + 0.01,
            bar.get_y() + bar.get_height() / 2,
            f"{val * 100:.2f}%",
            va="center",
            fontsize=8,
        )

    save(fig, "fig02_demand_capture")


def fig04_cliff_2019() -> None:
    """F4: Monthly revenue 2018–2019."""
    df = (
        _con()
        .execute(
            """
        select date_trunc('month', sales_date) as month,
               sum(revenue) as revenue
        from marts.mart_daily_executive_kpis
        where date_part('year', sales_date) in (2018, 2019)
        group by 1
        order by 1
        """
        )
        .fetchdf()
    )
    df["month"] = pd.to_datetime(df["month"])

    fig, ax = plt.subplots(figsize=(12, 4.5))
    mask18 = df["month"].dt.year == 2018
    mask19 = df["month"].dt.year == 2019
    ax.plot(
        df.loc[mask18, "month"],
        df.loc[mask18, "revenue"],
        color=C_PRIMARY,
        marker="o",
        ms=3,
        label="2018",
    )
    ax.plot(
        df.loc[mask19, "month"],
        df.loc[mask19, "revenue"],
        color=C_ALERT,
        marker="s",
        ms=3,
        label="2019",
    )
    ax.axvline(pd.Timestamp("2019-01-01"), color=C_ALERT, ls="--", lw=0.8, alpha=0.5)
    ax.set_title("Monthly Revenue: 2018 vs 2019 — The Structural Break")
    ax.set_ylabel("Revenue (VND)")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    ax.legend(frameon=False)
    save(fig, "fig04_cliff_2019")


def fig05_marketing_misalignment() -> None:
    """F5: Seasonality (left) + Promo efficiency (right)."""
    df_seas = (
        _con()
        .execute("select month, seasonal_index from marts.mart_seasonal_pattern order by month")
        .fetchdf()
    )
    df_promo = (
        _con()
        .execute(
            """
        select promo_type,
               round(sum(total_net_revenue) / nullif(sum(total_discount_amount), 0), 1) as roi,
               round(sum(total_discount_amount)::double / nullif(sum(total_gross_revenue), 0), 4) as discount_rate,
               count(*) as campaigns
        from marts.mart_promotion_effectiveness
        group by 1
        """
        )
        .fetchdf()
    )

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), gridspec_kw={"wspace": 0.35})
    # Left: seasonality
    colours = [
        C_PRIMARY if 4 <= m <= 6 else C_SECONDARY if m in [11, 12] else C_REF
        for m in df_seas["month"]
    ]
    ax1.bar(df_seas["month"], df_seas["seasonal_index"], color=colours, width=0.7)
    ax1.axhline(1.0, color="black", ls="-", lw=0.6)
    ax1.set_xlabel("Month")
    ax1.set_ylabel("Seasonal Index")
    ax1.set_title("Anti-Holiday Seasonality — Peaks in Spring")
    ax1.set_xticks(range(1, 13))
    ax1.set_xticklabels(["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"])

    # Right: promo efficiency
    sizes = df_promo["campaigns"] * 8
    colours2 = [C_PRIMARY, C_SECONDARY]
    for i, row in df_promo.iterrows():
        ax2.scatter(
            row["discount_rate"] * 100,
            row["roi"],
            s=sizes.iloc[i],
            c=colours2[i],
            alpha=0.7,
            edgecolors="white",
            zorder=3,
        )
        ax2.annotate(
            row["promo_type"],
            (row["discount_rate"] * 100, row["roi"]),
            textcoords="offset points",
            xytext=(5, 5),
            fontsize=8,
        )
    ax2.axvline(20, color=C_ALERT, ls="--", lw=0.7, alpha=0.5)
    ax2.text(20.5, ax2.get_ylim()[1] * 0.9, "20% diminishing\nreturns", color=C_ALERT, fontsize=8)
    ax2.set_xlabel("Discount Rate (%)")
    ax2.set_ylabel("ROI (Revenue / Discount)")
    ax2.set_title("Promo Efficiency: Fixed vs Percentage")

    save(fig, "fig05_marketing_misalignment")


def fig06_retention_clv() -> None:
    """F6: Retention curve + CLV Pareto."""
    df_ret = (
        _con()
        .execute(
            """
        select months_since_first_order, round(avg(retention_rate), 4) as rate
        from marts.mart_monthly_customer_cohort
        group by 1
        order by 1
        """
        )
        .fetchdf()
    )
    df_clv = (
        _con()
        .execute(
            """
        with d as (
            select customer_id, total_revenue,
                   ntile(10) over (order by total_revenue desc) as decile
            from marts.mart_customer_rfm
        )
        select decile,
               round(sum(total_revenue)::double / (select sum(total_revenue) from d), 4) as share
        from d
        group by 1
        order by 1
        """
        )
        .fetchdf()
    )

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), gridspec_kw={"wspace": 0.35})
    ax1.plot(
        df_ret["months_since_first_order"],
        df_ret["rate"] * 100,
        color=C_PRIMARY,
        marker="o",
        ms=3,
        lw=1.2,
    )
    ax1.axhline(5, color=C_ALERT, ls="--", lw=0.7, alpha=0.6)
    ax1.set_xlabel("Months Since First Order")
    ax1.set_ylabel("Retention Rate (%)")
    ax1.set_title("Cohort Retention Curve")
    ax1.set_xlim(0, 12)
    ax2.bar(df_clv["decile"], df_clv["share"] * 100, color=C_PRIMARY)
    ax2.axhline(10, color=C_REF, ls="--", lw=0.6)
    ax2.set_xlabel("Revenue Decile (1=Top 10%)")
    ax2.set_ylabel("Revenue Share (%)")
    ax2.set_title("Customer Revenue Concentration")
    save(fig, "fig06_retention_clv")


def fig07_portfolio_drift() -> None:
    """F7: Category scatter (left) + Revenue share donut (right)."""
    df_cat = (
        _con()
        .execute(
            """
        select category,
               round(sum(gross_revenue), 0) as revenue,
               round(sum(gross_profit)::double / nullif(sum(gross_revenue), 0), 4) as margin
        from marts.mart_monthly_category_performance
        group by 1
        """
        )
        .fetchdf()
    )

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), gridspec_kw={"wspace": 0.35})
    # Left: scatter
    ax1.scatter(
        df_cat["revenue"] / 1e9,
        df_cat["margin"] * 100,
        s=120,
        c=C_PRIMARY,
        alpha=0.7,
        edgecolors="white",
        zorder=3,
    )
    for _, row in df_cat.iterrows():
        ax1.annotate(
            row["category"],
            (row["revenue"] / 1e9, row["margin"] * 100),
            textcoords="offset points",
            xytext=(5, 5),
            fontsize=8,
        )
    ax1.axhline(15, color=C_ALERT, ls="--", lw=0.7, alpha=0.6)
    ax1.text(ax1.get_xlim()[1] * 0.95, 15.5, "15% target", color=C_ALERT, fontsize=8, ha="right")
    ax1.set_xlabel("Revenue (Billion VND)")
    ax1.set_ylabel("Gross Margin (%)")
    ax1.set_title("Portfolio Drift: Volume vs Profitability")

    # Right: donut
    total = df_cat["revenue"].sum()

    def _autopct(pct):
        return f"{pct:.1f}%" if pct >= 5.0 else ""

    colors = [C_PRIMARY, C_SECONDARY, C_TERTIARY, C_QUATERNARY]
    wedges, texts, autotexts = ax2.pie(
        df_cat["revenue"],
        labels=None,
        autopct=_autopct,
        startangle=90,
        colors=colors[: len(df_cat)],
        wedgeprops=dict(width=0.5, edgecolor="white"),
        textprops={"fontsize": 9},
        pctdistance=0.75,
    )
    ax2.legend(
        wedges,
        [
            f"{cat} ({rev / total * 100:.1f}%)"
            for cat, rev in zip(df_cat["category"], df_cat["revenue"])
        ],
        title="Category",
        loc="center left",
        bbox_to_anchor=(0.92, 0, 0.5, 1),
        frameon=False,
        fontsize=9,
    )
    ax2.set_title("Revenue Share by Category — Streetwear Dominates")

    save(fig, "fig07_portfolio_drift")


def fig09_quality_tax() -> None:
    """F9: Return trend (left) + Return reasons donut (right)."""
    df_trend = (
        _con()
        .execute(
            """
        select sales_date, return_record_rate
        from marts.mart_daily_returns_kpis
        order by sales_date
        """
        )
        .fetchdf()
    )
    df_trend["sales_date"] = pd.to_datetime(df_trend["sales_date"])

    df_reasons = (
        _con()
        .execute(
            """
        select 'defective' as reason, sum(defective_return_count) as cnt from marts.mart_daily_returns_kpis
        union all select 'wrong_size', sum(wrong_size_return_count) from marts.mart_daily_returns_kpis
        union all select 'not_as_described', sum(not_as_described_return_count) from marts.mart_daily_returns_kpis
        union all select 'changed_mind', sum(changed_mind_return_count) from marts.mart_daily_returns_kpis
        union all select 'late_delivery', sum(late_delivery_return_count) from marts.mart_daily_returns_kpis
        order by cnt desc
        """
        )
        .fetchdf()
    )

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), gridspec_kw={"wspace": 0.35})
    # Left: trend
    ax1.plot(df_trend["sales_date"], df_trend["return_record_rate"] * 100, color=C_PRIMARY, lw=0.8)
    ax1.axhline(5, color=C_ALERT, ls="--", lw=0.7)
    ax1.set_title("Daily Return Rate Trend")
    ax1.set_ylabel("Return Rate (%)")
    ax1.xaxis.set_major_locator(mdates.YearLocator())
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    # Right: donut
    colors = [C_ALERT, C_SECONDARY, C_QUATERNARY, C_PRIMARY, C_REF]
    wedges, texts, autotexts = ax2.pie(
        df_reasons["cnt"],
        labels=None,
        autopct="%1.1f%%",
        startangle=90,
        colors=colors[: len(df_reasons)],
        wedgeprops=dict(width=0.5, edgecolor="white"),
        textprops={"fontsize": 9},
        pctdistance=0.75,
    )
    ax2.legend(
        wedges,
        df_reasons["reason"],
        title="Reason",
        loc="center left",
        bbox_to_anchor=(0.92, 0, 0.5, 1),
        frameon=False,
        fontsize=9,
    )
    ax2.set_title("Return Reasons — Wrong Size and Defective Are Controllable")

    save(fig, "fig09_quality_tax")


def fig10_operational_drags() -> None:
    """F10: COD cancel (left) + Geographic puzzle (right)."""
    df_cod = (
        _con()
        .execute(
            """
        select case when payment_method = 'cod' then 'COD' else 'Prepaid' end as group,
               round(sum(cancelled_lines)::double / nullif(sum(order_line_count), 0), 4) as rate
        from marts.mart_daily_payment_checkout_kpis
        where payment_method != 'unknown'
        group by 1
        """
        )
        .fetchdf()
    )
    df_geo = (
        _con()
        .execute(
            """
        select region, round(total_revenue, 0) as revenue,
               round(return_unit_rate, 4) as ret_rate
        from marts.mart_region_fulfillment_profile
        order by revenue desc
        """
        )
        .fetchdf()
    )

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), gridspec_kw={"wspace": 0.35})
    # Left: COD
    ax1.bar(df_cod["group"], df_cod["rate"] * 100, color=[C_PRIMARY, C_SECONDARY])
    ax1.set_ylabel("Cancellation Rate (%)")
    ax1.set_title("COD Cancellation vs Prepaid")
    for i, v in enumerate(df_cod["rate"]):
        ax1.text(i, v * 100 + 0.2, f"{v * 100:.1f}%", ha="center", fontsize=8)

    # Right: geographic
    x = np.arange(len(df_geo))
    ax3 = ax2
    ax3.bar(x, df_geo["revenue"] / 1e9, color=C_PRIMARY, alpha=0.7)
    ax3.set_ylabel("Revenue (B VND)", color=C_PRIMARY)
    ax4 = ax3.twinx()
    ax4.plot(x, df_geo["ret_rate"] * 100, color=C_ALERT, marker="o", ms=4)
    ax4.set_ylabel("Return Rate (%)", color=C_ALERT)
    ax3.set_xticks(x)
    ax3.set_xticklabels(df_geo["region"])
    ax3.set_title("Revenue vs Return Rate by Region")

    save(fig, "fig10_operational_drags")


def fig12_inventory_bloat() -> None:
    """F12: Lifecycle horizontal bar (left) + Days of supply (right)."""
    df_life = (
        _con()
        .execute(
            """
        select lifecycle_stage, count(*) as products, round(sum(total_revenue), 0) as total_revenue
        from marts.mart_product_lifetime_performance
        group by 1
        order by total_revenue desc
        """
        )
        .fetchdf()
    )
    df_inv = (
        _con()
        .execute(
            """
        select sales_date, avg_days_of_supply
        from marts.mart_monthly_inventory_snapshot
        order by sales_date
        """
        )
        .fetchdf()
    )
    df_inv["sales_date"] = pd.to_datetime(df_inv["sales_date"])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), gridspec_kw={"wspace": 0.35})
    # Left: lifecycle
    colours = [C_PRIMARY, C_SECONDARY, C_TERTIARY, C_ALERT]
    bars = ax1.barh(df_life["lifecycle_stage"], df_life["products"], color=colours, height=0.6)
    ax1.set_xlabel("Product Count")
    ax1.set_title("Product Lifecycle: Catalog Bloat Revealed")
    ax1.invert_yaxis()
    for bar, val in zip(bars, df_life["products"]):
        ax1.text(
            bar.get_width() + 20,
            bar.get_y() + bar.get_height() / 2,
            f"{val:,}",
            va="center",
            fontsize=8,
        )

    # Right: inventory
    ax2.plot(df_inv["sales_date"], df_inv["avg_days_of_supply"], color=C_PRIMARY, lw=0.8)
    ax2.axhline(90, color=C_ALERT, ls="--", lw=0.7)
    ax2.text(df_inv["sales_date"].max(), 95, "90-day target", color=C_ALERT, fontsize=8, ha="right")
    ax2.set_title("Days of Supply Over Time")
    ax2.set_ylabel("Days")
    ax2.xaxis.set_major_locator(mdates.YearLocator())
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    save(fig, "fig12_inventory_bloat")


def fig13_channel_economics() -> None:
    """F13: Channel efficiency (left) + LTV vs churn (right)."""
    df_eff = (
        _con()
        .execute(
            """
        with c as (
            select acquisition_channel,
                   round(avg(total_revenue), 0) as ltv,
                   round(sum(case when total_orders = 1 then 1 else 0 end)::double / count(*), 4) as churn
            from marts.mart_customer_rfm
            group by 1
        )
        select *, round(ltv * (1 - churn), 0) as efficiency from c order by efficiency desc
        """
        )
        .fetchdf()
    )
    df_ltv = (
        _con()
        .execute(
            """
        select acquisition_channel,
               round(avg(total_revenue), 0) as avg_ltv,
               round(sum(case when total_orders = 1 then 1 else 0 end)::double / count(*), 4) as single_order_rate
        from marts.mart_customer_rfm
        group by 1
        order by avg_ltv desc
        """
        )
        .fetchdf()
    )

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), gridspec_kw={"wspace": 0.35})
    # Left: efficiency
    ax1.barh(df_eff["acquisition_channel"], df_eff["efficiency"], color=C_PRIMARY)
    ax1.set_xlabel("Efficiency Score (LTV × Retention)")
    ax1.set_title("Channel Efficiency Ranking")
    ax1.invert_yaxis()

    # Right: LTV vs churn
    x = np.arange(len(df_ltv))
    ax2.bar(x, df_ltv["avg_ltv"], color=C_PRIMARY, alpha=0.8, label="Avg LTV")
    ax2.set_ylabel("Avg LTV (VND)", color=C_PRIMARY)
    ax2.tick_params(axis="y", labelcolor=C_PRIMARY)
    ax2.set_xticks(x)
    ax2.set_xticklabels(df_ltv["acquisition_channel"], rotation=30, ha="right", fontsize=8)
    ax3 = ax2.twinx()
    ax3.plot(
        x,
        df_ltv["single_order_rate"] * 100,
        color=C_ALERT,
        marker="o",
        ms=4,
        lw=1.2,
        label="Single-Order Rate",
    )
    ax3.set_ylabel("Single-Order Rate (%)", color=C_ALERT)
    ax3.tick_params(axis="y", labelcolor=C_ALERT)
    ax3.axhline(25, color=C_REF, ls="--", lw=0.6)
    ax2.set_title("Channel Economics: LTV vs Churn Risk")
    lines1, labels1 = ax2.get_legend_handles_labels()
    lines2, labels2 = ax3.get_legend_handles_labels()
    ax2.legend(
        lines1 + lines2,
        labels1 + labels2,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.25),
        frameon=False,
        ncol=2,
        fontsize=8,
    )

    save(fig, "fig13_channel_economics")


def fig19_cohort_heatmap() -> None:
    """F19: Cohort retention heatmap (channel × age)."""
    df = (
        _con()
        .execute(
            """
        select acquisition_channel, age_group,
               round(avg(case when months_since_first_order = 1 then retention_rate end), 4) as m1_retention
        from marts.mart_cohort_by_channel_age
        group by 1, 2
        order by 1, 2
        """
        )
        .fetchdf()
    )
    pivot = df.pivot(
        index="acquisition_channel", columns="age_group", values="m1_retention"
    ).fillna(0)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    im = ax.imshow(pivot.values, cmap="YlOrRd", aspect="auto", vmin=0, vmax=0.15)
    ax.set_xticks(np.arange(len(pivot.columns)))
    ax.set_yticks(np.arange(len(pivot.index)))
    ax.set_xticklabels(pivot.columns, fontsize=9)
    ax.set_yticklabels(pivot.index, fontsize=9)
    ax.set_xlabel("Age Group")
    ax.set_ylabel("Acquisition Channel")
    ax.set_title("Month-1 Retention Heatmap — Channel × Age")
    for i in range(len(pivot.index)):
        for j in range(len(pivot.columns)):
            val = pivot.values[i, j]
            text_color = "white" if val > 0.08 else "black"
            ax.text(j, i, f"{val:.1%}", ha="center", va="center", color=text_color, fontsize=8)
    cbar = fig.colorbar(im, ax=ax, shrink=0.6)
    cbar.set_label("M1 Retention", rotation=270, labelpad=15)
    save(fig, "fig19_cohort_heatmap")


# ═══════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════

ALL_FIGURES = [
    fig01_revenue_cogs_profit,
    fig02_demand_capture,
    fig04_cliff_2019,
    fig05_marketing_misalignment,
    fig06_retention_clv,
    fig07_portfolio_drift,
    fig09_quality_tax,
    fig10_operational_drags,
    fig12_inventory_bloat,
    fig13_channel_economics,
    fig19_cohort_heatmap,
]


def main() -> None:
    print(f"Output directory: {OUTPUT_DIR}")
    for fn in ALL_FIGURES:
        print(f"Generating {fn.__name__} ...")
        try:
            fn()
        except Exception as exc:
            print(f"  ERROR: {exc}")
    print("Done.")


if __name__ == "__main__":
    main()
