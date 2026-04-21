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

## Revenue vs COGS

Shows top-line scale and margin pressure trend.

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

## Traffic and Orders

Tracks demand capture and conversion throughput.

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

Tracks daily product returns in units.

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

Shows promotional spend trend that can erode margin.

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
