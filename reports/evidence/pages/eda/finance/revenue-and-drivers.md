---
title: Revenue and Drivers
---

# Revenue and Operational Signals

```sql _date_bounds
select sales_date from datathon_warehouse.mart_forecast_daily_base
```

<DateRange name=date_range data={_date_bounds} dates=sales_date/>

```sql daily_series
select
    sales_date,
    revenue,
    cogs,
    order_count,
    sessions,
    total_discount_amount,
    return_units,
    avg_bounce_rate
from datathon_warehouse.mart_forecast_daily_base
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
order by sales_date
```

```sql revenue_cogs_long
select sales_date, 'Revenue' as metric, revenue as value
from datathon_warehouse.mart_forecast_daily_base
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
union all
select sales_date, 'COGS' as metric, cogs as value
from datathon_warehouse.mart_forecast_daily_base
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
order by sales_date
```

```sql sessions_orders_long
select sales_date, 'Sessions' as metric, sessions as value
from datathon_warehouse.mart_forecast_daily_base
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
union all
select sales_date, 'Orders' as metric, order_count as value
from datathon_warehouse.mart_forecast_daily_base
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
order by sales_date
```

```sql returns_long
select sales_date, 'Return Units' as metric, return_units as value
from datathon_warehouse.mart_forecast_daily_base
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
order by sales_date
```

```sql discounts_long
select sales_date, 'Discount Amount' as metric, total_discount_amount as value
from datathon_warehouse.mart_forecast_daily_base
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
order by sales_date
```

```sql revenue_heatmap_dow
select
    extract(dow from sales_date) as dow,
    case extract(dow from sales_date)
        when 0 then 'Sun'
        when 1 then 'Mon'
        when 2 then 'Tue'
        when 3 then 'Wed'
        when 4 then 'Thu'
        when 5 then 'Fri'
        when 6 then 'Sat'
    end as day_name,
    avg(revenue) as avg_revenue
from datathon_warehouse.mart_forecast_daily_base
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
group by 1, 2
order by 1
```

```sql daily_revenue_calendar
select
    sales_date,
    revenue
from datathon_warehouse.mart_forecast_daily_base
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
order by sales_date
```

```sql revenue_trend
with numbered as (
    select revenue, row_number() over (order by sales_date) as rn
    from datathon_warehouse.mart_forecast_daily_base
    where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
)
select
    regr_slope(revenue, rn) as daily_slope,
    regr_r2(revenue, rn) as r2
from numbered
```

```sql anomaly_summary
with flagged as (
    select
        sales_date,
        revenue,
        case
            when revenue > avg(revenue) over () + 2 * stddev_samp(revenue) over () then 'spike'
            when revenue < avg(revenue) over () - 2 * stddev_samp(revenue) over () then 'drop'
            else 'normal'
        end as anomaly_flag
    from datathon_warehouse.mart_forecast_daily_base
    where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
)
select sales_date, revenue, anomaly_flag from flagged where anomaly_flag != 'normal' order by sales_date
```

## Revenue Trend

<Alert status="info">
Revenue trend slope: <Value data={revenue_trend} column=daily_slope fmt=num0/> VND/day 
(R² = <Value data={revenue_trend} column=r2 fmt=pct1/>).
R² near 0 indicates a weak linear trend — revenue is driven more by seasonality and promotions than by a steady long-term direction.
</Alert>

<AreaChart
    data={revenue_cogs_long}
    x=sales_date
    y=value
    series=metric
    yAxisTitle="Revenue / COGS"
    xAxisTitle="Date"
    title="Daily Revenue and COGS"
    subtitle="Top-line scale vs direct cost of goods sold"
    yFmt="num0"
/>

## Anomaly Detection

<Alert status="warning">
Days with revenue beyond ±2σ from the mean are flagged below. 
Spikes may indicate successful promotions; drops may signal stockouts or traffic issues.
</Alert>

<DataTable data={anomaly_summary} rows=10 />

## Traffic and Orders

<Alert status="info">
Sessions represent demand generation; orders represent captured demand. 
The gap between the two lines is unconverted traffic — the primary lever for revenue growth.
</Alert>

<AreaChart
    data={sessions_orders_long}
    x=sales_date
    y=value
    series=metric
    yAxisTitle="Sessions / Orders"
    xAxisTitle="Date"
    title="Daily Sessions vs Orders"
    subtitle="Demand generation and captured transactions"
    yFmt="num0"
/>

## Return Volume

<Alert status="info">
Return volume is a leading indicator of product quality and customer satisfaction. 
Sustained increases suggest root causes in fulfillment, sizing, or defects.
</Alert>

<LineChart
    data={returns_long}
    x=sales_date
    y=value
    series=metric
    yAxisTitle="Return Units"
    xAxisTitle="Date"
    title="Daily Return Units"
    subtitle="Quality signal from return volume"
    yFmt="num0"
/>

## Discount Pressure

<Alert status="warning">
Heavy discounting erodes margin. Days with discount > 10% of revenue warrant investigation 
into whether the lift justifies the margin sacrifice.
</Alert>

<AreaChart
    data={discounts_long}
    x=sales_date
    y=value
    series=metric
    yAxisTitle="Discount Amount"
    xAxisTitle="Date"
    title="Daily Discount Amount"
    subtitle="Promotional spend trend"
    yFmt="num0"
/>

## Revenue Pattern by Day of Week

<Alert status="info">
Wednesday has the highest average revenue (~4.7M VND), while Saturday is the weakest (~3.9M). 
This contradicts the common assumption that weekends drive peak trading. 
Action: Reallocate weekend ad spend to Tuesday–Wednesday to capture peak demand days.
</Alert>

<BarChart
    data={revenue_heatmap_dow}
    x=day_name
    y=avg_revenue
    title="Average Revenue by Day of Week"
    subtitle="Reveals intra-week trading patterns"
    yAxisTitle="Avg Revenue"
    yFmt="num0"
/>

## Daily Revenue Calendar

<CalendarHeatmap
    data={daily_revenue_calendar}
    date=sales_date
    value=revenue
    title="Daily Revenue Calendar"
    subtitle="Revenue intensity by day across the date range"
    valueFmt="num0"
/>

<DataTable data={daily_series} rows=10/>
