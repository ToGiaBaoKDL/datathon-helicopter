---
title: The Inventory Capital Trap
---

<Alert status="warning">
<b>The question:</b> <Value data={inventory_overview} column=days_supply fmt=0/> days of supply (~<Value data={inventory_years} column=years fmt=0.0/> years) with a <Value data={inventory_overview} column=sell_through fmt=pct2/> sell-through rate. 
Working capital is severely tied up in slow-moving stock. Where is the money trapped?
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

```sql inventory_turns
select round(avg(avg_sell_through_rate), 2) as turns
from datathon_warehouse.mart_monthly_inventory_snapshot
```

```sql lifecycle_summary
select
    lifecycle_stage,
    count(*) as products,
    round(sum(total_revenue), 0) as total_revenue,
    round(sum(total_revenue) / count(*), 0) as rev_per_sku
from datathon_warehouse.mart_product_lifetime_performance
group by 1
order by total_revenue desc
```

```sql monthly_inventory_trend
select
    sales_date,
    avg_days_of_supply,
    avg_sell_through_rate,
    stockout_product_count,
    overstock_product_count
from datathon_warehouse.mart_monthly_inventory_snapshot
order by sales_date
```

```sql never_sold_count
select count(*) as never_sold_products
from datathon_warehouse.mart_product_lifetime_performance
where lifecycle_stage = 'never_sold'
```

```sql never_sold_detail
select
    category,
    count(*) as products
from datathon_warehouse.mart_product_lifetime_performance
where lifecycle_stage = 'never_sold'
group by 1
order by products desc
```

```sql active_efficiency
select
    round(sum(total_revenue) / count(*), 0) as active_rev_per_sku,
    count(*) as active_products
from datathon_warehouse.mart_product_lifetime_performance
where lifecycle_stage = 'active'
```

```sql discontinued_efficiency
select
    round(sum(total_revenue) / count(*), 0) as disc_rev_per_sku,
    count(*) as discontinued_products
from datathon_warehouse.mart_product_lifetime_performance
where lifecycle_stage = 'discontinued'
```

```sql active_disc_ratio
select
    round(
        (select sum(total_revenue)::double / count(*) from datathon_warehouse.mart_product_lifetime_performance where lifecycle_stage = 'active')
        / nullif((select sum(total_revenue)::double / count(*) from datathon_warehouse.mart_product_lifetime_performance where lifecycle_stage = 'discontinued'), 0),
        1
    ) as ratio
```

```sql daily_stockout_calendar
select
    sales_date,
    stockout_product_count as value
from datathon_warehouse.mart_monthly_inventory_snapshot
order by sales_date
```

```sql what_if_inventory
with inventory_stats as (
    select round(avg(avg_days_of_supply), 0) as days_supply
    from datathon_warehouse.mart_monthly_inventory_snapshot
),
cogs_stats as (
    select round(avg(cogs), 0) as avg_daily_cogs
    from datathon_warehouse.mart_daily_executive_kpis
)
select
    days_supply,
    avg_daily_cogs,
    days_supply - 90 as excess_days,
    round((days_supply - 90) * avg_daily_cogs, 0) as capital_freed,
    round((days_supply - 90) * avg_daily_cogs * 12, 0) as annual_working_capital_cycle
from inventory_stats, cogs_stats
```

## 1. The Scale: Years of Supply

<Alert status="info">
The business carries <b><Value data={inventory_overview} column=days_supply fmt=0/> days</b> of supply on average — roughly <Value data={inventory_years} column=years fmt=0.0/> years. 
With a sell-through rate of only <Value data={inventory_overview} column=sell_through fmt=pct2/>, inventory turns <Value data={inventory_turns} column=turns fmt=0.00/>× per year. 
Healthy retail turns inventory 4–6× per year (60–90 days).
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

## 2. Lifecycle: Where Capital Is Trapped

<Alert status="info">
<Value data={never_sold_count} column=never_sold_products fmt=0/> SKUs have never sold a single unit. 
<Value data={discontinued_efficiency} column=discontinued_products fmt=0/> discontinued SKUs generate revenue but at <b>half</b> the efficiency of active products. 
The majority of the catalog is dead weight.
</Alert>

<BarChart
    data={lifecycle_summary}
    x=lifecycle_stage
    y=products
    title="Product Count by Lifecycle Stage"
    subtitle="Most SKUs are dead weight — never_sold or discontinued"
    yAxisTitle="Products"
    yFmt="num0"
/>

<BarChart
    data={lifecycle_summary}
    x=lifecycle_stage
    y=total_revenue
    title="Total Revenue by Lifecycle Stage"
    subtitle="Active products concentrate revenue; never_sold generates nothing"
    yAxisTitle="Revenue (VND)"
    yFmt="num0"
/>

## 3. Efficiency: Active vs Discontinued

<Alert status="info">
Active products generate <Value data={active_efficiency} column=active_rev_per_sku fmt=num0/> VND/SKU.
Discontinued products generate <Value data={discontinued_efficiency} column=disc_rev_per_sku fmt=num0/> VND/SKU.
Active is <b><Value data={active_disc_ratio} column=ratio fmt=0.0/>×</b> more efficient.
</Alert>

<BarChart
    data={lifecycle_summary}
    x=lifecycle_stage
    y=rev_per_sku
    title="Avg Revenue per Product by Lifecycle Stage"
    subtitle="Active SKUs are dramatically more productive than discontinued"
    yAxisTitle="Revenue per SKU"
    yFmt="num0"
>
    <ReferenceLine y=10000000 label="10M VND/SKU" hideValue=true color=info/>
</BarChart>

## 4. Trend: Structural, Not Seasonal

<Alert status="info">
Stockout product count reveals supply reliability. A rising trend means procurement or logistics
is failing to keep up with catalog breadth. A falling trend suggests either improved fulfillment
or shrinking assortment.
</Alert>

<LineChart
    data={monthly_inventory_trend}
    x=sales_date
    y=stockout_product_count
    title="Stockout Product Count Over Time"
    subtitle="How many products are simultaneously out of stock each month"
    yAxisTitle="Stockout Products"
    yFmt="0"
>
    <ReferenceLine y=100 label="100 Alert" hideValue=true color=negative lineType=dashed/>
</LineChart>

<LineChart
    data={monthly_inventory_trend}
    x=sales_date
    y=avg_days_of_supply
    title="Days of Supply Over Time"
    subtitle="Inventory bloat is structural, not seasonal"
    yAxisTitle="Days of Supply"
    yFmt="0"
/>

<LineChart
    data={monthly_inventory_trend}
    x=sales_date
    y=avg_sell_through_rate
    title="Sell-Through Rate Over Time"
    subtitle="Sell-through sits well below healthy retail benchmarks"
    yAxisTitle="Sell-Through Rate"
    yFmt="pct2"
>
    <ReferenceLine y=0.30 label="30% Healthy" hideValue=true color=positive lineType=dashed/>
</LineChart>

<Alert status="info">
The calendar below shows stockout product count by day. Values are derived from monthly inventory snapshots forward-filled to daily grain — 
so each month's value persists across all days in that month. Darker cells = more products out of stock simultaneously.
Clusters reveal systemic inventory gaps, not random shortages.
</Alert>

<CalendarHeatmap
    data={daily_stockout_calendar}
    date=sales_date
    value=value
    title="Daily Stockout Product Count"
    subtitle="Inventory gaps over time — clusters signal systemic supply issues"
    valueFmt="0"
/>

## 5. Never-Sold Breakdown

<Alert status="info">
<Value data={never_sold_count} column=never_sold_products fmt=0/> SKUs have never sold a single unit. 
These products tie up catalog complexity, warehouse space, and procurement overhead with zero return.
The breakdown by category shows which merchandising teams are carrying the most dead weight.
</Alert>

<BarChart
    data={never_sold_detail}
    x=category
    y=products
    swapXY=true
    title="Never-Sold Products by Category"
    subtitle="Dead stock concentration by category"
    yAxisTitle="Products"
    yFmt="num0"
/>

## 6. What-If: Right-Sizing Inventory

<Alert status="info">
Industry standard is 90 days of supply. The business currently carries <Value data={what_if_inventory} column=days_supply fmt=0/> days.
Right-sizing to 90 days would free up <Value data={what_if_inventory} column=capital_freed fmt=num0/> VND in working capital.
That is equivalent to <Value data={what_if_inventory} column=annual_working_capital_cycle fmt=num0/> VND over a full 12-month inventory cycle.
</Alert>

<Grid cols=3>
    <BigValue
        data={what_if_inventory}
        value=days_supply
        title="Current Days of Supply"
        fmt="0"
    />
    <BigValue
        data={what_if_inventory}
        value=excess_days
        title="Excess Days vs 90"
        fmt="0"
    />
    <BigValue
        data={what_if_inventory}
        value=capital_freed
        title="Capital Freed (VND)"
        fmt="num0"
    />
</Grid>

## The Verdict

<Alert status="positive">
<b>Action:</b> Target 90 days of supply (industry standard).
Delist <Value data={never_sold_count} column=never_sold_products fmt=0/> never_sold SKUs immediately — they generate zero revenue and tie up catalog complexity.
Run clearance on dormant. Active products are <b><Value data={active_disc_ratio} column=ratio fmt=0.0/>×</b> more productive than discontinued — prioritize active replenishment over expanding SKU count.
See also <a href="/02-eda/operations/03-inventory-and-growth-scorecard">Inventory and Growth Scorecard</a> for operational inventory metrics.
</Alert>

## Deep Dive

- [Inventory And Growth Scorecard](/02-eda/operations/03-inventory-and-growth-scorecard)
- [Product Lifecycle And Health](/02-eda/product/01-product-lifecycle-and-health)

