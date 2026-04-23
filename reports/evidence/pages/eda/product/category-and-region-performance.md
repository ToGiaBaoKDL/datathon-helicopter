---
title: Category and Region Performance
---

# Category and Region Performance

This page explains where growth and margin are coming from across portfolio and geography.

```sql _date_bounds
select sales_date from datathon_warehouse.mart_daily_executive_kpis
```

```sql _categories
select distinct category from datathon_warehouse.mart_monthly_category_performance order by 1
```

```sql _regions
select distinct region from datathon_warehouse.mart_weekly_region_performance order by 1
```

<DateRange
    name=date_range
    data={_date_bounds}
    dates=sales_date
/>

<Dropdown
    name=cat_filter
    data={_categories}
    value=category
    multiple=true
    selectAllByDefault=true
    title="Category"
/>

<Dropdown
    name=region_filter
    data={_regions}
    value=region
    multiple=true
    selectAllByDefault=true
    title="Region"
/>

```sql category_monthly
select
    month_start_date,
    category,
    segment,
    gross_revenue,
    gross_profit,
    gross_margin_rate,
    cancelled_revenue_share,
    return_unit_rate
from datathon_warehouse.mart_monthly_category_performance
where month_start_date >= date_trunc('month', cast('${inputs.date_range.start}' as date))
  and month_start_date <= date_trunc('month', cast('${inputs.date_range.end}' as date))
  and category in ${inputs.cat_filter.value}
order by month_start_date, category, segment
```

```sql region_weekly
select
    week_start_date,
    region,
    gross_revenue,
    gross_profit,
    gross_margin_rate,
    active_customer_count,
    order_count,
    return_units,
    refund_amount
from datathon_warehouse.mart_weekly_region_performance
where week_start_date >= date_trunc('week', cast('${inputs.date_range.start}' as date))
  and week_start_date <= date_trunc('week', cast('${inputs.date_range.end}' as date))
  and region in ${inputs.region_filter.value}
order by week_start_date, region
```

## Monthly Category Margin

<Alert status="info">
Category margin trajectories reveal pricing power and cost discipline. Categories consistently below 
the 15% target margin may need repricing, cost reduction, or SKU rationalization.
</Alert>

<Alert status="warning">
359 products have negative realized margin due to deep discounting. These SKUs drag down category averages 
and should be reviewed for delisting or repricing.
</Alert>

<LineChart
    data={category_monthly}
    x=month_start_date
    y=gross_margin_rate
    series=category
    title="Monthly Gross Margin by Category"
    subtitle="Margin trajectory across selected product categories"
    yAxisTitle="Gross Margin Rate"
    xAxisTitle="Month"
    yFmt="0.0%"
>
    <ReferenceLine y=0.15 label="15% Target" hideValue=true color=positive/>
</LineChart>

## Weekly Revenue by Region

<Alert status="info">
Geographic revenue patterns reveal market maturity and growth opportunity. 
Regions with declining revenue but stable active customers indicate AOV erosion — a pricing problem, not a demand problem.
</Alert>

<LineChart
    data={region_weekly}
    x=week_start_date
    y=gross_revenue
    series=region
    title="Weekly Revenue by Region"
    subtitle="Geographic revenue contribution over time"
    yAxisTitle="Revenue"
    xAxisTitle="Week"
    yFmt="num0"
/>

## Weekly Active Customers by Region

<Alert status="info">
Customer base growth by region indicates market penetration success. 
Regions where revenue grows faster than active customers are improving monetization; the reverse suggests acquisition without retention.
</Alert>

<LineChart
    data={region_weekly}
    x=week_start_date
    y=active_customer_count
    series=region
    title="Weekly Active Customers by Region"
    subtitle="Customer base growth by geography"
    yAxisTitle="Active Customers"
    xAxisTitle="Week"
    yFmt="num0"
/>

## Category Detail

<DataTable data={category_monthly} rows=10/>

## Region Detail

<DataTable data={region_weekly} rows=10/>
