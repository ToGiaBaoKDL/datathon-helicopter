---
title: The Inventory Capital Trap
---

# The Inventory Capital Trap

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

## 1. The Scale: 2.5 Years of Supply

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
Active is <b><Value data={active_disc_ratio} column=ratio fmt=0.0x/></b> more efficient.
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

## 5. Never-Sold Breakdown

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

## The Verdict

<Alert status="positive">
<b>Action:</b> Target 90 days of supply (industry standard). 
Delist <Value data={never_sold_count} column=never_sold_products fmt=0/> never_sold SKUs immediately — they generate zero revenue and tie up catalog complexity. 
Run clearance on dormant. Active products are <b><Value data={active_disc_ratio} column=ratio fmt=0.0x/></b> more productive than discontinued — prioritize active replenishment over expanding SKU count.
</Alert>
