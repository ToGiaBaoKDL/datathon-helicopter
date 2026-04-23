---
title: Product Lifecycle and Health
---

# Product Lifecycle and Health

This page monitors product portfolio health through lifecycle stages, return rates, and inventory signals.

```sql _date_bounds
select sales_date from datathon_warehouse.mart_daily_executive_kpis
```

```sql _categories
select distinct category from datathon_warehouse.mart_product_lifetime_performance order by 1
```

```sql _lifecycle_stages
select distinct lifecycle_stage from datathon_warehouse.mart_product_lifetime_performance order by 1
```

<DateRange
    name=date_range
    data={_date_bounds}
    dates=sales_date
/>

<Dropdown
    name=category_filter
    data={_categories}
    value=category
    multiple=true
    selectAllByDefault=true
    title="Category"
/>

<Dropdown
    name=stage_filter
    data={_lifecycle_stages}
    value=lifecycle_stage
    multiple=true
    selectAllByDefault=true
    title="Lifecycle Stage"
/>

```sql lifecycle_distribution
select
    lifecycle_stage,
    count(*) as products,
    sum(total_revenue) as total_revenue,
    avg(realized_margin_rate) as avg_margin_rate,
    avg(return_unit_rate) as avg_return_rate
from datathon_warehouse.mart_product_lifetime_performance
where category in ${inputs.category_filter.value}
  and lifecycle_stage in ${inputs.stage_filter.value}
group by 1
order by total_revenue desc
```

```sql category_pareto
select
    category,
    count(*) as products,
    sum(total_revenue) as total_revenue,
    sum(gross_profit) as total_profit,
    avg(realized_margin_rate) as avg_margin_rate
from datathon_warehouse.mart_product_lifetime_performance
where lifecycle_stage != 'never_sold'
  and category in ${inputs.category_filter.value}
  and lifecycle_stage in ${inputs.stage_filter.value}
group by 1
order by total_revenue desc
```

```sql top_returned
select
    product_name,
    category,
    total_revenue,
    return_unit_rate,
    return_units
from datathon_warehouse.mart_product_lifetime_performance
where lifecycle_stage != 'never_sold'
  and category in ${inputs.category_filter.value}
  and lifecycle_stage in ${inputs.stage_filter.value}
order by return_unit_rate desc
limit 10
```

```sql monthly_health_trend
select
    month_start_date,
    avg(return_unit_rate) as avg_return_rate,
    avg(sell_through_rate) as avg_sell_through,
    sum(stockout_flag) as stockout_products,
    sum(overstock_flag) as overstock_products
from datathon_warehouse.mart_monthly_product_health
where month_start_date >= date_trunc('month', cast('${inputs.date_range.start}' as date))
  and month_start_date <= date_trunc('month', cast('${inputs.date_range.end}' as date))
group by 1
order by 1
```

```sql lifecycle_margin
select
    lifecycle_stage,
    category,
    count(*) as products,
    avg(realized_margin_rate) as avg_margin_rate,
    avg(return_unit_rate) as avg_return_rate
from datathon_warehouse.mart_product_lifetime_performance
where lifecycle_stage != 'never_sold'
  and category in ${inputs.category_filter.value}
  and lifecycle_stage in ${inputs.stage_filter.value}
group by 1, 2
order by lifecycle_stage, avg_margin_rate desc
```

```sql revenue_share_top10
select
    product_name,
    category,
    total_revenue,
    revenue_share_in_category,
    lifecycle_stage
from datathon_warehouse.mart_product_lifetime_performance
where lifecycle_stage != 'never_sold'
  and category in ${inputs.category_filter.value}
  and lifecycle_stage in ${inputs.stage_filter.value}
order by total_revenue desc
limit 10
```

## Lifecycle Distribution

<Alert status="info">
Lifecycle stages reveal portfolio vitality. "Active" products (sold within last 6 months) are the revenue engine. 
"Dormant" and "discontinued" products tie up working capital and catalog complexity without generating sales.
</Alert>

<Alert status="warning">
359 sold products have negative realized margin (COGS > net revenue after discounts), reflecting deep promotional discounting. 
These SKUs destroy value on every sale — consider delisting or repricing.
</Alert>

<BarChart
    data={lifecycle_distribution}
    x=lifecycle_stage
    y=products
    title="Product Count by Lifecycle Stage"
    subtitle="Portfolio composition: active, dormant, discontinued, never_sold"
    yAxisTitle="Products"
    yFmt="num0"
/>

<BarChart
    data={lifecycle_distribution}
    x=lifecycle_stage
    y=total_revenue
    title="Revenue by Lifecycle Stage"
    subtitle="Where revenue is concentrated in the portfolio"
    yAxisTitle="Revenue"
    yFmt="num0"
/>

## Category Pareto

<Alert status="info">
Category revenue follows a Pareto pattern — a small number of categories drive the majority of revenue. 
Margin rate varies significantly by category, revealing where pricing power is strongest.
</Alert>

<BarChart
    data={category_pareto}
    x=category
    y=total_revenue
    title="Lifetime Revenue by Category"
    subtitle="Category contribution to total sold-product revenue"
    yAxisTitle="Revenue"
    yFmt="num0"
/>

<BarChart
    data={category_pareto}
    x=category
    y=avg_margin_rate
    title="Average Realized Margin by Category"
    subtitle="Post-discount margin performance"
    yAxisTitle="Margin Rate"
    yFmt="0.0%"
/>

## Monthly Health Trend

<Alert status="warning">
Return rate is a leading quality indicator. Sustained elevation above 5% signals systematic issues 
in product quality, sizing, or fulfillment damage. Stockout count above 100 products indicates broad availability risk.
</Alert>

<LineChart
    data={monthly_health_trend}
    x=month_start_date
    y=avg_return_rate
    title="Monthly Average Return Rate"
    subtitle="Quality trend across the product portfolio"
    yAxisTitle="Return Rate"
    xAxisTitle="Month"
    yFmt="0.0%"
>
    <ReferenceLine y=0.05 label="5% Quality Threshold" hideValue=true color=negative/>
</LineChart>

<LineChart
    data={monthly_health_trend}
    x=month_start_date
    y=stockout_products
    title="Monthly Stockout Product Count"
    subtitle="Inventory availability pressure over time"
    yAxisTitle="Products"
    xAxisTitle="Month"
    yFmt="num0"
>
    <ReferenceLine y=100 label="Alert Level" hideValue=true color=warning/>
</LineChart>

## Top Returned Products

<Alert status="info">
High-return products destroy margin twice — once on the sale, once on reverse logistics. 
Products with return rates above 20% should trigger immediate quality review or supplier negotiation.
</Alert>

<DataTable data={top_returned} rows=10 />

## Top 10 Products by Revenue

<Alert status="info">
Revenue concentration in top products creates portfolio risk. If the top 10 products face 
stockout or quality issues, the revenue impact is disproportionate.
</Alert>

<DataTable data={revenue_share_top10} rows=10 />

## Lifecycle x Category Margin Matrix

<Alert status="info">
The margin matrix reveals which lifecycle-category combinations are profitable. 
"Active" products in high-margin categories are the crown jewels; "dormant" products with negative margin are liabilities.
</Alert>

<DataTable data={lifecycle_margin} rows=10 />
