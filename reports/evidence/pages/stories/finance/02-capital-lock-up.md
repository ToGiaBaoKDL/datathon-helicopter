---
title: The Capital Lock-Up
---

<Alert status="warning">
<b>The question:</b> <Value data={inventory_overview} column=days_supply fmt=0/> days of supply. 
<Value data={never_sold_count} column=never_sold_products fmt=0/> SKUs that have never sold. 
How much working capital is trapped in slow-moving and dead stock?
</Alert>

```sql inventory_overview
select
    round(avg(avg_days_of_supply), 0) as days_supply,
    round(avg(avg_sell_through_rate), 4) as sell_through,
    round(avg(stockout_product_count), 0) as stockout_products,
    round(avg(overstock_product_count), 0) as overstock_products
from datathon_warehouse.mart_monthly_inventory_snapshot
```

```sql inventory_years
select round(avg(avg_days_of_supply) / 365.0, 1) as years
from datathon_warehouse.mart_monthly_inventory_snapshot
```

```sql never_sold_count
select count(*) as never_sold_products
from datathon_warehouse.mart_product_lifetime_performance
where lifecycle_stage = 'never_sold'
```

```sql lifecycle_capital
select
    lifecycle_stage,
    count(*) as products,
    round(sum(total_revenue), 0) as total_revenue,
    round(avg(total_revenue), 0) as avg_revenue_per_sku
from datathon_warehouse.mart_product_lifetime_performance
group by 1
order by total_revenue desc
```

```sql capital_opportunity
with inventory_stats as (
    select round(avg(avg_days_of_supply), 0) as current_days
    from datathon_warehouse.mart_monthly_inventory_snapshot
),
cogs_stats as (
    select round(avg(cogs), 0) as avg_daily_cogs
    from datathon_warehouse.mart_daily_executive_kpis
)
select
    current_days,
    90 as target_days,
    current_days - 90 as excess_days,
    round((current_days - 90) * avg_daily_cogs, 0) as capital_freed,
    round((current_days - 90) * avg_daily_cogs * 12, 0) as annual_working_capital_cycle
from inventory_stats, cogs_stats
```

```sql inventory_trend
select
    sales_date,
    avg_days_of_supply,
    stockout_product_count,
    overstock_product_count
from datathon_warehouse.mart_monthly_inventory_snapshot
order by sales_date
```

## 1. The Scale: Years of Supply Trapped

<Alert status="info">
The business carries <b><Value data={inventory_overview} column=days_supply fmt=0/> days</b> of supply — roughly <Value data={inventory_years} column=years fmt=0.0/> years. 
Healthy retail operates at 60–90 days. 
The excess is <b><Value data={inventory_overview} column=days_supply fmt=0/> − 90</b> days of tied-up capital.
</Alert>

<Grid cols=4>
    <BigValue
        data={inventory_overview}
        value=days_supply
        title="Days of Supply"
        fmt="0"
    />
    <BigValue
        data={inventory_overview}
        value=sell_through
        title="Sell-Through Rate"
        fmt="pct2"
    />
    <BigValue
        data={inventory_overview}
        value=stockout_products
        title="Stockout Products"
        fmt="0"
    />
    <BigValue
        data={inventory_overview}
        value=overstock_products
        title="Overstock Products"
        fmt="0"
    />
</Grid>

## 2. Capital by Lifecycle: Where the Money Sleeps

<Alert status="info">
Never_sold and discontinued SKUs tie up capital with minimal or zero return. 
Active SKUs are productive but overstocked.
</Alert>

<BarChart
    data={lifecycle_capital}
    x=lifecycle_stage
    y=products
    title="Product Count by Lifecycle Stage"
    subtitle="Never_sold SKUs are pure capital traps"
    yAxisTitle="Products"
    yFmt="num0"
/>

<BarChart
    data={lifecycle_capital}
    x=lifecycle_stage
    y=avg_revenue_per_sku
    title="Avg Revenue per SKU by Lifecycle"
    subtitle="Active SKUs are productive; never_sold generates nothing"
    yAxisTitle="Revenue per SKU"
    yFmt="num0"
/>

## 3. The Opportunity: What If Supply Normalized?

<Alert status="info">
If days of supply dropped from <Value data={capital_opportunity} column=current_days fmt=0/> to 90 days (industry standard),
<Value data={capital_opportunity} column=capital_freed fmt=num0/> VND in working capital would be freed.
Over a 12-month cycle, that is <Value data={capital_opportunity} column=annual_working_capital_cycle fmt=num0/> VND available for reinvestment in marketing, product development, or debt reduction.
</Alert>

<Grid cols=3>
    <BigValue
        data={capital_opportunity}
        value=current_days
        title="Current Days of Supply"
        fmt="0"
    />
    <BigValue
        data={capital_opportunity}
        value=excess_days
        title="Excess Days vs 90"
        fmt="0"
    />
    <BigValue
        data={capital_opportunity}
        value=capital_freed
        title="Capital Freed (VND)"
        fmt="num0"
    />
</Grid>

## 4. Trend: Structural Bloat

<Alert status="info">
Days of supply has remained structurally elevated over the entire dataset period.
This is not a cyclical spike — it is a chronic inventory management failure.
Without intervention, working capital will continue to be trapped in slow-moving stock.
</Alert>

<LineChart
    data={inventory_trend}
    x=sales_date
    y=avg_days_of_supply
    title="Days of Supply Over Time"
    subtitle="Inventory bloat is structural, not cyclical"
    yAxisTitle="Days of Supply"
    yFmt="0"
/>

## The Verdict

<Alert status="positive">
<b>Action:</b> Working capital is severely trapped in slow-moving inventory.
Delist <Value data={never_sold_count} column=never_sold_products fmt=0/> never_sold SKUs immediately — they generate zero revenue and consume shelf space.
Target 90 days of supply. The freed capital can be reinvested in high-ROI marketing or product innovation.
See also <a href="/stories/product/01-inventory-capital-trap">Story 01: The Inventory Capital Trap</a> for lifecycle-stage analysis and SKU efficiency breakdown.
</Alert>

## Deep Dive

- [Inventory And Growth Scorecard](/eda/operations/03-inventory-and-growth-scorecard)

