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
where month_start_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
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

<DataTable data={top_returned} rows=10 />

## Top 10 Products by Revenue

<DataTable data={revenue_share_top10} rows=10 />

## Lifecycle x Category Margin Matrix

<DataTable data={lifecycle_margin} rows=10 />
