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

```sql yoy_monthly_growth
with monthly as (
    select
        date_trunc('month', sales_date) as month_start,
        sum(revenue) as monthly_revenue,
        sum(cogs) as monthly_cogs,
        sum(order_count) as monthly_orders,
        sum(cancelled_line_count) as monthly_cancelled
    from datathon_warehouse.mart_forecast_daily_base
    where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
    group by 1
)
select
    month_start,
    monthly_revenue,
    monthly_cogs,
    monthly_orders,
    monthly_cancelled,
    monthly_cancelled::double / nullif(monthly_orders, 0) as cancellation_rate,
    lag(monthly_revenue) over (order by month_start) as prev_month_revenue,
    lag(monthly_revenue, 12) over (order by month_start) as yoy_revenue,
    (monthly_revenue - prev_month_revenue) / nullif(prev_month_revenue, 0) as mom_growth,
    (monthly_revenue - yoy_revenue) / nullif(yoy_revenue, 0) as yoy_growth
from monthly
order by month_start
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

```sql anomaly_bounds
select
    avg(revenue) - 2 * stddev_samp(revenue) as lower_bound,
    avg(revenue) + 2 * stddev_samp(revenue) as upper_bound,
    avg(revenue) as mean_revenue
from datathon_warehouse.mart_forecast_daily_base
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
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
</Alert>

<Alert status="warning">
R² = 8.8% means the linear model explains almost nothing. The real story is a <b>structural break</b>: 
revenue rose to a peak in 2016 (~5.75M/day) then collapsed after 2018 to ~2.9M/day — a 50% drop. 
This is not gradual decline; it's a regime change. The cause: conversion collapse (1.2% → 0.3%), not traffic loss.
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
>
    <ReferenceArea data={anomaly_bounds} yMin=lower_bound yMax=upper_bound color=gray opacity=0.1/>
</AreaChart>

## Anomaly Detection

<Alert status="warning">
Days with revenue beyond the shaded ±2σ band (gray area on chart above) are flagged below. 
Spikes may indicate successful promotions; drops may signal stockouts or traffic issues.
</Alert>

<Alert status="info">
<b>How to read:</b> The gray band on the Revenue and COGS chart represents the "normal" range (mean ± 2 standard deviations). 
Points outside this band are statistically unusual — not just bad/good days, but genuinely anomalous.
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

## Monthly Growth: MoM and YoY

<Alert status="info">
Month-over-month (MoM) growth captures short-term momentum shifts. 
Year-over-year (YoY) growth eliminates seasonality and reveals true underlying trajectory.
</Alert>

<Alert status="positive">
<b>Business best practice:</b> Always compare YoY for seasonal businesses. A "bad" month might just be seasonally weak — 
YoY tells you if performance is actually declining relative to the same period last year.
</Alert>

<BarChart
    data={yoy_monthly_growth}
    x=month_start
    y=yoy_growth
    title="Year-over-Year Revenue Growth"
    subtitle="Same month vs prior year — eliminates seasonality"
    yAxisTitle="YoY Growth"
    yFmt="0.0%"
>
    <ReferenceLine y=0 label="Zero Growth" hideValue=true color=info/>
</BarChart>

<BarChart
    data={yoy_monthly_growth}
    x=month_start
    y=mom_growth
    title="Month-over-Month Revenue Growth"
    subtitle="Sequential monthly change — captures momentum"
    yAxisTitle="MoM Growth"
    yFmt="0.0%"
>
    <ReferenceLine y=0 label="Zero Growth" hideValue=true color=info/>
</BarChart>

## Cancellation Rate Trend

<Alert status="warning">
<b>~10% of order lines are cancelled</b> on average — this is lost revenue before it even ships. 
Cancellation rate is a leading indicator of inventory availability, pricing errors, or checkout friction.
</Alert>

<Alert status="positive">
Action: If cancellation spikes correlate with stockout days, it's an inventory signal. 
If it correlates with deep discounts, it's a pricing/promo code issue.
</Alert>

<LineChart
    data={yoy_monthly_growth}
    x=month_start
    y=cancellation_rate
    title="Monthly Cancellation Rate"
    subtitle="Share of order lines cancelled before fulfillment"
    yAxisTitle="Cancellation Rate"
    yFmt="0.0%"
>
    <ReferenceLine y=0.10 label="10% Alert" hideValue=true color=warning/>
</LineChart>

<DataTable data={daily_series} rows=10/>
