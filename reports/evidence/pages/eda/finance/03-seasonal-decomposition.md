---
title: Seasonal Decomposition and Predictive Signals
---

This page dissects revenue into seasonal patterns and uses historical trends to surface
predictive signals for demand planning. It answers: *when does revenue peak, and how predictable is it?*

```sql _date_bounds
select sales_date from datathon_warehouse.mart_forecast_daily_base
```

<DateRange
    name=date_range
    data={_date_bounds}
    dates=sales_date
/>

```sql seasonal_index
select
    month,
    avg_revenue,
    overall_avg_revenue,
    seasonal_index,
    revenue_deviation
from datathon_warehouse.mart_seasonal_pattern
order by month
```

```sql monthly_revenue
select
    date_trunc('month', sales_date) as month_start,
    sum(revenue) as revenue,
    sum(cogs) as cogs,
    sum(order_count) as orders
from datathon_warehouse.mart_forecast_daily_base
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
group by 1
order by 1
```

```sql yoy_growth
select
    date_trunc('month', sales_date) as month_start,
    sum(revenue) as revenue,
    lag(sum(revenue)) over (order by date_trunc('month', sales_date)) as prev_month_revenue,
    lag(sum(revenue), 12) over (order by date_trunc('month', sales_date)) as prev_year_revenue
from datathon_warehouse.mart_forecast_daily_base
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
group by 1
order by 1
```

```sql dow_pattern
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
    avg(revenue) as avg_revenue,
    avg(order_count) as avg_orders
from datathon_warehouse.mart_forecast_daily_base
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
group by 1, 2
order by 1
```

```sql monthly_with_index
select
    mr.month_start,
    mr.revenue,
    sp.seasonal_index,
    sp.revenue_deviation
from (
    select
        date_trunc('month', sales_date) as month_start,
        sum(revenue) as revenue
    from datathon_warehouse.mart_forecast_daily_base
    where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
    group by 1
) mr
left join datathon_warehouse.mart_seasonal_pattern sp
    on extract(month from mr.month_start) = sp.month
order by mr.month_start
```

```sql yoy_clean
select
    month_start,
    revenue,
    prev_year_revenue,
    case when prev_year_revenue > 0
        then (revenue - prev_year_revenue) / prev_year_revenue
        else null
    end as yoy_growth_rate
from ${yoy_growth}
where prev_year_revenue is not null
order by month_start
```

```sql daily_with_ma
select
    sales_date,
    revenue,
    avg(revenue) over (order by sales_date rows between 29 preceding and current row) as ma_30d
from datathon_warehouse.mart_forecast_daily_base
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
order by sales_date
```

## Seasonal Index by Month

<Alert status="info">
The seasonal index compares each month's average revenue to the yearly average.
Values above 1.0 mean above-average months (peak season); below 1.0 mean below-average (trough).
The seasonal index shows clear peaks and troughs — some months consistently outperform others.
</Alert>

<Alert status="positive">
Action: Reallocate marketing budget toward April-May peak season. The Nov-Dec trough
suggests the business does not benefit from year-end holiday shopping — investigate whether
competitor promotions or product-seasonality mismatch cause this.
</Alert>

<AreaChart
    data={seasonal_index}
    x=month
    y=seasonal_index
    title="Seasonal Revenue Index by Month"
    subtitle="1.0 = yearly average. Above 1 = peak, below 1 = trough"
    yAxisTitle="Seasonal Index"
    yFmt="0.00"
>
    <ReferenceLine y=1 label="Yearly Average" hideValue=true color=info/>
    <ReferenceArea xMin=4 xMax=6 label="Peak Season (Apr-May-Jun)" color=positive opacity=0.18/>
    <ReferenceArea xMin=11 xMax=12 label="Trough (Nov-Dec)" color=warning opacity=0.18/>
    <ReferenceArea xMin=1 xMax=1 label="Trough (Jan)" color=warning opacity=0.18/>
</AreaChart>

<BarChart
    data={seasonal_index}
    x=month
    y=revenue_deviation
    title="Revenue Deviation from Yearly Average"
    subtitle="Absolute VND difference by month"
    yAxisTitle="Deviation"
    yFmt="num0"
>
    <ReferenceLine y=0 label="Baseline" hideValue=true color=info/>
</BarChart>

## Monthly Revenue Trend

<Alert status="info">
Overlaying actual monthly revenue with the seasonal index reveals how much of the movement
is predictable seasonality vs one-off events. Months that deviate sharply from the index
suggest external shocks (promos, stockouts, competitor actions).
</Alert>

<AreaChart
    data={monthly_revenue}
    x=month_start
    y=revenue
    title="Monthly Revenue Trend"
    subtitle="Revenue trajectory with seasonal overlay"
    yAxisTitle="Revenue"
    yFmt="num0"
/>

<LineChart
    data={monthly_with_index}
    x=month_start
    y=revenue
    title="Monthly Revenue with Seasonal Deviation"
    subtitle="Actual revenue vs seasonal expectation"
    yAxisTitle="Revenue"
    yFmt="num0"
/>

## Day-of-Week Pattern

<Alert status="info">
Day-of-week patterns reveal operational rhythms. Strong weekday performance suggests
B2B or office-shopping behaviour. Weekend spikes suggest leisure shopping.
</Alert>

<BarChart
    data={dow_pattern}
    x=day_name
    y=avg_orders
    sort=false
    title="Average Orders by Day of Week"
    subtitle="Weekly order volume pattern"
    yAxisTitle="Avg Orders"
    yFmt="0"
/>

## Predictive Signal: YoY Growth

<Alert status="warning">
YoY growth stripping out seasonality reveals the underlying business trajectory.
Sustained negative YoY growth means the business is shrinking in real terms — 
seasonal peaks merely mask structural decline.
</Alert>

<LineChart
    data={yoy_clean}
    x=month_start
    y=yoy_growth_rate
    title="Year-over-Year Revenue Growth"
    subtitle="Stripping seasonality to see true business trajectory"
    yAxisTitle="YoY Growth"
    yFmt="pct2"
>
    <ReferenceLine y=0 label="Zero Growth" hideValue=true color=warning/>
</LineChart>

## Daily Revenue with Moving Average

<Alert status="info">
The 30-day moving average smooths daily noise and reveals the trend component.
When daily revenue consistently runs below the moving average, demand is decelerating.
When above, demand is accelerating.
</Alert>

<LineChart
    data={daily_with_ma}
    x=sales_date
    y=revenue
    title="Daily Revenue with 30-Day Moving Average"
    subtitle="Trend smoothing to identify inflection points"
    yAxisTitle="Revenue"
    yFmt="num0"
/>

<Alert status="info">
The 30-day moving average smooths daily noise. When daily revenue consistently runs below the MA, demand is decelerating; when above, accelerating.
</Alert>

## Seasonal Pattern Summary

<DataTable data={seasonal_index} rows=12>
    <Column id=month title="Month" fmt=0/>
    <Column id=avg_revenue title="Avg Revenue" fmt=num0/>
    <Column id=overall_avg_revenue title="Yearly Avg" fmt=num0/>
    <Column id=seasonal_index title="Index" fmt=0.00/>
    <Column id=revenue_deviation title="Deviation" fmt=num0/>
</DataTable>

## Related Stories

- [04 Seasonality Paradox](/stories/marketing/04-seasonality-paradox)

