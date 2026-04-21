---
title: Executive KPI Pulse
---

# Executive KPI Pulse

This page provides a quick daily pulse across revenue, demand, fulfillment, inventory, and quality.

```sql _date_bounds
select sales_date from datathon_warehouse.mart_daily_executive_kpis
```

```sql _years
select distinct date_part('year', sales_date) as year
from datathon_warehouse.mart_daily_executive_kpis
order by 1
```

<DateRange
    name=date_range
    data={_date_bounds}
    dates=sales_date
/>

<Dropdown
    name=year_filter
    data={_years}
    value=year
    title="Year"
/>

```sql executive_daily
select
    sales_date,
    revenue,
    gross_margin_rate,
    order_count,
    sessions,
    session_to_order_rate,
    return_record_rate,
    avg_days_to_deliver,
    avg_stockout_days,
    wow_revenue_growth_rate,
    wow_order_growth_rate
from datathon_warehouse.mart_daily_executive_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
  and date_part('year', sales_date) = '${inputs.year_filter.value}'
order by sales_date
```

```sql latest_snapshot
select
    sales_date,
    revenue,
    gross_margin_rate,
    order_count,
    session_to_order_rate,
    return_record_rate,
    avg_days_to_deliver,
    avg_stockout_days,
    wow_revenue_growth_rate,
    wow_order_growth_rate
from datathon_warehouse.mart_daily_executive_kpis
where sales_date <= '${inputs.date_range.end}'
order by sales_date desc
limit 1
```

```sql revenue_long
select sales_date, 'Revenue' as metric, revenue as value
from datathon_warehouse.mart_daily_executive_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
  and date_part('year', sales_date) = '${inputs.year_filter.value}'
order by sales_date
```

```sql mean_revenue
select avg(revenue) as mean_revenue
from datathon_warehouse.mart_daily_executive_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
  and date_part('year', sales_date) = '${inputs.year_filter.value}'
```

```sql rates_long
select sales_date, 'Gross Margin Rate' as metric, gross_margin_rate as value
from datathon_warehouse.mart_daily_executive_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
  and date_part('year', sales_date) = '${inputs.year_filter.value}'
union all
select sales_date, 'Session to Order Rate' as metric, session_to_order_rate as value
from datathon_warehouse.mart_daily_executive_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
  and date_part('year', sales_date) = '${inputs.year_filter.value}'
union all
select sales_date, 'Return Record Rate' as metric, return_record_rate as value
from datathon_warehouse.mart_daily_executive_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
  and date_part('year', sales_date) = '${inputs.year_filter.value}'
order by sales_date
```

```sql ops_risk_long
select sales_date, 'Avg Days to Deliver' as metric, avg_days_to_deliver as value
from datathon_warehouse.mart_daily_executive_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
  and date_part('year', sales_date) = '${inputs.year_filter.value}'
union all
select sales_date, 'Avg Stockout Days' as metric, avg_stockout_days as value
from datathon_warehouse.mart_daily_executive_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
  and date_part('year', sales_date) = '${inputs.year_filter.value}'
order by sales_date
```

```sql conversion_by_dow
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
    avg(session_to_order_rate) as avg_conversion_rate
from datathon_warehouse.mart_daily_executive_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
  and date_part('year', sales_date) = '${inputs.year_filter.value}'
  and sessions > 0
group by 1, 2
order by 1
```

```sql quarterly_summary
select
    date_part('year', sales_date) as year,
    date_part('quarter', sales_date) as quarter,
    avg(revenue) as avg_revenue,
    sum(gross_profit) / sum(revenue) as avg_margin,
    sum(order_count) / sum(sessions) as avg_conversion,
    avg(return_record_rate) as avg_return_rate
from datathon_warehouse.mart_daily_executive_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
  and date_part('year', sales_date) = '${inputs.year_filter.value}'
group by 1, 2
order by 1, 2
```

```sql monthly_seasonality
select
    date_part('month', sales_date) as month,
    avg(revenue) as avg_revenue,
    avg(order_count) as avg_orders
from datathon_warehouse.mart_daily_executive_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
  and date_part('year', sales_date) = '${inputs.year_filter.value}'
group by 1
order by 1
```

## Latest Snapshot

<DataTable data={latest_snapshot} rows=10 />

## Revenue Trend

<AreaChart
    data={revenue_long}
    x=sales_date
    y=value
    series=metric
    title="Daily Revenue"
    subtitle="Top-line revenue movement over time"
    xAxisTitle="Date"
    yAxisTitle="Revenue"
    yFmt="num0"
>
    <ReferenceLine data={mean_revenue} y=mean_revenue label="Avg" hideValue=true color=info/>
</AreaChart>

## Rate Signals

<LineChart
    data={rates_long}
    x=sales_date
    y=value
    series=metric
    title="Margin, Conversion, and Return Rates"
    subtitle="Key performance ratios on a comparable scale"
    xAxisTitle="Date"
    yAxisTitle="Rate"
    yFmt="0.0%"
/>

## Operational Risk Signals

<LineChart
    data={ops_risk_long}
    x=sales_date
    y=value
    series=metric
    title="Delivery and Stockout Risk"
    subtitle="Lower is better for both delivery time and stockout exposure"
    xAxisTitle="Date"
    yAxisTitle="Risk Level"
    yFmt="0"
/>

## Conversion Pattern by Day of Week

<BarChart
    data={conversion_by_dow}
    x=day_name
    y=avg_conversion_rate
    title="Average Session-to-Order Rate by Day of Week"
    subtitle="Identifies weekly demand-capture patterns"
    yAxisTitle="Conversion Rate"
    yFmt="0.0%"
/>

## Monthly Seasonality

<BarChart
    data={monthly_seasonality}
    x=month
    y=avg_revenue
    title="Average Daily Revenue by Month"
    subtitle="Reveals annual seasonal patterns"
    yAxisTitle="Revenue"
    xAxisTitle="Month"
    yFmt="num0"
>
    <ReferenceLine data={mean_revenue} y=mean_revenue label="Avg" hideValue=true color=info/>
</BarChart>

## Quarterly Summary

<DataTable data={quarterly_summary} rows=10 />

## Daily Detail

<DataTable data={executive_daily} rows=10 />
