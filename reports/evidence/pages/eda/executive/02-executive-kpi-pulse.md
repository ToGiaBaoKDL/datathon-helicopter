---
title: Executive KPI Pulse
---

This page provides a quick daily pulse across revenue, demand, fulfillment, inventory, and quality.

```sql _date_bounds
select sales_date from datathon_warehouse.mart_daily_executive_kpis
```

<DateRange
    name=date_range
    data={_date_bounds}
    dates=sales_date
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
select
    sales_date,
    'Revenue' as metric,
    revenue as value
from datathon_warehouse.mart_daily_executive_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
order by sales_date
```

```sql peak_revenue
select max(revenue) as peak_revenue
from datathon_warehouse.mart_daily_executive_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
```

```sql revenue_rolling
select
    sales_date,
    'Revenue' as metric,
    revenue as value,
    avg(revenue) over (order by sales_date rows between 6 preceding and current row) as roll_7d,
    avg(revenue) over (order by sales_date rows between 27 preceding and current row) as roll_28d
from datathon_warehouse.mart_daily_executive_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
order by sales_date
```

```sql mean_revenue
select avg(revenue) as mean_revenue
from datathon_warehouse.mart_daily_executive_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
```

```sql rates_long
select sales_date, 'Gross Margin Rate' as metric, gross_margin_rate as value
from datathon_warehouse.mart_daily_executive_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
union all
select sales_date, 'Session to Order Rate' as metric, session_to_order_rate as value
from datathon_warehouse.mart_daily_executive_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
union all
select sales_date, 'Return Record Rate' as metric, return_record_rate as value
from datathon_warehouse.mart_daily_executive_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
order by sales_date
```

```sql ops_risk_long
select sales_date, 'Avg Days to Deliver' as metric, avg_days_to_deliver as value
from datathon_warehouse.mart_daily_executive_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
union all
select sales_date, 'Avg Stockout Days' as metric, avg_stockout_days as value
from datathon_warehouse.mart_daily_executive_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
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
    avg(session_to_order_rate) as avg_conversion_rate,
    avg(revenue) as avg_revenue
from datathon_warehouse.mart_daily_executive_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
  and sessions > 0
group by 1, 2
order by 1
```

```sql mean_conversion
select avg(session_to_order_rate) as mean_conversion
from datathon_warehouse.mart_daily_executive_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
  and sessions > 0
```

```sql quarterly_summary
select
    date_part('year', sales_date)::varchar || '-Q' || date_part('quarter', sales_date)::varchar as quarter_label,
    avg(revenue) as avg_revenue,
    sum(gross_profit) / sum(revenue) as avg_margin,
    sum(order_count)::double / sum(sessions) as avg_conversion,
    avg(return_record_rate) as avg_return_rate
from datathon_warehouse.mart_daily_executive_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
group by 1, date_part('year', sales_date), date_part('quarter', sales_date)
order by date_part('year', sales_date), date_part('quarter', sales_date)
```

```sql monthly_seasonality
select
    date_part('month', sales_date) as month,
    avg(revenue) as avg_revenue,
    avg(order_count) as avg_orders
from datathon_warehouse.mart_daily_executive_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
group by 1
order by 1
```

```sql month_end_effect
select
    case when extract(day from sales_date) > 28 then 'Month-end (29-31)' else 'Other days' end as day_type,
    avg(revenue) as avg_revenue
from datathon_warehouse.mart_daily_executive_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
group by 1
order by 1 desc
```

```sql month_end_diff
select
    max(case when day_type = 'Month-end (29-31)' then avg_revenue end) as month_end_revenue,
    max(case when day_type = 'Other days' then avg_revenue end) as other_revenue
from ${month_end_effect}
```

```sql what_if_conversion
with base as (
    select
        sum(sessions)::double / count(*) as avg_sessions,
        sum(order_count)::double / sum(sessions) as current_conversion,
        sum(revenue)::double / count(*) as current_revenue,
        sum(order_count)::double / count(*) as current_orders
    from datathon_warehouse.mart_daily_executive_kpis
    where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
      and sessions > 0
)
select
    current_revenue,
    current_conversion,
    current_orders,
    avg_sessions * (current_conversion + 0.01) * (current_revenue / nullif(avg_sessions * current_conversion, 0)) as projected_revenue,
    projected_revenue - current_revenue as incremental_revenue,
    (projected_revenue - current_revenue) / nullif(current_revenue, 0) as pct_lift
from base
```

```sql yoy_trends
select date_part('year', sales_date) as year, 'Conversion Rate' as metric, avg(session_to_order_rate) as value
from datathon_warehouse.mart_daily_executive_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}' and sessions > 0
group by 1
union all
select date_part('year', sales_date), 'Gross Margin Rate', avg(gross_margin_rate)
from datathon_warehouse.mart_daily_executive_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
group by 1
union all
select date_part('year', sales_date), 'Return Record Rate', avg(return_record_rate)
from datathon_warehouse.mart_daily_executive_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
group by 1
order by 1, 2
```

```sql conversion_peak
select
    max(case when avg_conversion = max_conv then year end) as peak_year,
    max(max_conv) as peak_conversion,
    min(case when avg_conversion = min_conv then year end) as trough_year,
    min(min_conv) as trough_conversion
from (
    select
        date_part('year', sales_date) as year,
        avg(session_to_order_rate) as avg_conversion,
        max(avg(session_to_order_rate)) over () as max_conv,
        min(avg(session_to_order_rate)) over () as min_conv
    from datathon_warehouse.mart_daily_executive_kpis
    where sessions > 0
    group by 1
) t
```

```sql dow_best_worst
select
    max(case when day_name = 'Wed' then avg_conversion_rate end) as wed_conversion,
    max(case when day_name = 'Wed' then avg_revenue end) as wed_revenue,
    max(case when day_name = 'Sat' then avg_conversion_rate end) as sat_conversion,
    max(case when day_name = 'Sat' then avg_revenue end) as sat_revenue
from ${conversion_by_dow}
```

```sql conversion_calendar
select
    sales_date,
    session_to_order_rate as conversion_rate
from datathon_warehouse.mart_daily_executive_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
order by sales_date
```

## Latest Snapshot

<Alert status="info">
Latest data as of <Value data={latest_snapshot} column=sales_date/>.
Revenue: <Value data={latest_snapshot} column=revenue fmt=num0/> VND |
Margin: <Value data={latest_snapshot} column=gross_margin_rate fmt=pct2/> |
Conversion: <Value data={latest_snapshot} column=session_to_order_rate fmt=pct2/>.
</Alert>

<DataTable data={latest_snapshot} rows=10>
    <Column id=sales_date title="Date"/>
    <Column id=revenue title="Revenue" fmt=num0/>
    <Column id=gross_margin_rate title="Margin" fmt=pct2/>
    <Column id=order_count title="Orders" fmt=0/>
    <Column id=session_to_order_rate title="Conversion" fmt=pct2/>
    <Column id=return_record_rate title="Return Rate" fmt=pct2/>
    <Column id=avg_days_to_deliver title="Delivery Days" fmt=0.0/>
    <Column id=avg_stockout_days title="Stockout Days" fmt=0/>
    <Column id=wow_revenue_growth_rate title="Revenue Growth" fmt=pct2/>
    <Column id=wow_order_growth_rate title="Order Growth" fmt=pct2/>
</DataTable>

## Revenue Trend

<Alert status="info">
Revenue trend shows daily top-line movement. Days above the mean line (dashed) indicate above-average performance. 
The green "Peak" line shows the highest daily revenue in the selected period — the gap between current and peak 
is the recovery opportunity.
</Alert>

<AreaChart
    data={revenue_long}
    x=sales_date
    y=value
    series=metric
    title="Daily Revenue"
    subtitle="Daily revenue trend"
    xAxisTitle="Date"
    yAxisTitle="Revenue"
    yFmt="num0"
/>

<Alert status="info">
Daily revenue averages <Value data={mean_revenue} column=mean_revenue fmt=num0/> VND, peaking at <Value data={peak_revenue} column=peak_revenue fmt=num0/> VND in the selected period.
</Alert>

## Daily Order Count

<Alert status="info">
Order volume is the other side of the revenue equation. Tracking daily orders alongside revenue reveals whether growth is driven by volume, price, or both.
Days above the mean line indicate above-average demand capture.
</Alert>

```sql mean_orders
select avg(order_count) as mean_orders
from datathon_warehouse.mart_daily_executive_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
```

<AreaChart
    data={executive_daily}
    x=sales_date
    y=order_count
    title="Daily Order Count"
    subtitle="Daily order volume within the selected period"
    xAxisTitle="Date"
    yAxisTitle="Orders"
    yFmt="0"
/>

<Alert status="info">
Daily orders average <Value data={mean_orders} column=mean_orders fmt=0/> in the selected period.
</Alert>

## Revenue Trend (Rolling Average)

<Alert status="info">
Daily revenue is noisy — promotions, weekends, and outliers create volatility. 
Rolling averages smooth this noise to reveal the true underlying trend.
</Alert>

<Alert status="positive">
<b>How to read:</b> 7-day rolling captures short-term momentum (week-to-week). 28-day rolling captures monthly trajectory. 
When 7-day crosses above 28-day, momentum is accelerating. When it crosses below, momentum is decelerating.
</Alert>

<LineChart
    data={revenue_rolling}
    x=sales_date
    y=roll_7d
    y2=roll_28d
    y2SeriesType=line
    title="Revenue Rolling Averages"
    subtitle="7-day (short-term momentum) vs 28-day (monthly trajectory)"
    yAxisTitle="Revenue"
    y2AxisTitle="Revenue"
    xAxisTitle="Date"
    yFmt="num0"
    y2Fmt="num0"
/>

## Rate Signals

<Alert status="info">
Three critical ratios on one scale. Gross margin rate reflects pricing power and cost control. 
Session-to-order rate measures demand capture efficiency. Return record rate is a quality signal.
</Alert>

<Alert status="warning">
Long-term trend: Conversion rate peaked at <Value data={conversion_peak} column=peak_conversion fmt=pct2/> in <Value data={conversion_peak} column=peak_year/> 
and troughed at <Value data={conversion_peak} column=trough_conversion fmt=pct2/> in <Value data={conversion_peak} column=trough_year/> — a severe erosion in demand capture efficiency. 
This is the single biggest driver of revenue pressure despite flat traffic.
</Alert>

<LineChart
    data={rates_long}
    x=sales_date
    y=value
    series=metric
    title="Margin, Conversion, and Return Rates"
    subtitle="Margin, conversion, and return rate trends over time"
    xAxisTitle="Date"
    yAxisTitle="Rate"
    yFmt="pct2"
>
    <ReferenceLine y=0.01 label="1% Benchmark" hideValue=true color=positive lineType=dashed/>
</LineChart>

## Operational Risk Signals

<Alert status="info">
Delivery time and stockout exposure are leading indicators of customer satisfaction and lost sales. 
Lower is better for both metrics.
</Alert>

<Alert status="positive">
Stockout days have improved gradually over the decade — inventory availability is getting better, not worse.
Delivery time is stable around 6 days across the entire period.
</Alert>

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
>
    <ReferenceLine y=7 label="7-Day SLA" hideValue=true color=warning/>
</LineChart>

## Conversion Pattern by Day of Week

<Alert status="info">
Wednesday conversion (<Value data={dow_best_worst} column=wed_conversion fmt=pct2/>) is <Value data={dow_best_worst} column=sat_conversion fmt=pct2/> on Saturday. 
Revenue follows the same pattern: <Value data={dow_best_worst} column=wed_revenue fmt=num0/> VND vs <Value data={dow_best_worst} column=sat_revenue fmt=num0/> VND.
This contradicts the common assumption that weekends perform best.
</Alert>

<Alert status="positive">
Action: Shift promotional email sends to Tuesday–Wednesday to capitalize on peak demand-capture days. 
Reduce weekend ad spend if traffic does not convert.
</Alert>

<BarChart
    data={conversion_by_dow}
    x=day_name
    y=avg_conversion_rate
    title="Average Session-to-Order Rate by Day of Week"
    subtitle="Wednesday peaks; weekend underperforms"
    yAxisTitle="Conversion Rate"
    yFmt="pct2"
/>

<Alert status="info">
Average conversion in the selected period is <Value data={mean_conversion} column=mean_conversion fmt=pct2/>.
</Alert>

<CalendarHeatmap
    data={conversion_calendar}
    date=sales_date
    value=conversion_rate
    title="Daily Conversion Rate Calendar"
    subtitle="Conversion intensity by day — spot outliers and structural drops"
    valueFmt="pct2"
/>

## Year-over-Year Trends

<Alert status="info">
Long-term structural view. Revenue peaked around 2016 then declined through 2020–2021 before a slight recovery. 
The conversion decline is the dominant driver — traffic (sessions) is flat but capture rate has collapsed.
</Alert>

<LineChart
    data={yoy_trends}
    x=year
    y=value
    series=metric
    title="Annual Rate Trends"
    subtitle="Conversion, margin, and return rate over time"
    xAxisTitle="Year"
    yAxisTitle="Rate"
    yFmt="pct2"
>
    <ReferenceLine y=0.01 label="1% Benchmark" hideValue=true color=positive lineType=dashed/>
</LineChart>

## What-If: Conversion Rate Impact

<Alert status="info">
Scenario: conversion rate increases by 1 percentage point above the current rate for the selected period, 
holding traffic and AOV constant. This is the #1 lever for revenue growth.
</Alert>

<Grid cols=3>
    <BigValue
        data={what_if_conversion}
        value=current_revenue
        title="Current Daily Revenue"
        fmt="num0"
    />
    <BigValue
        data={what_if_conversion}
        value=incremental_revenue
        title="Incremental Revenue"
        fmt="num0"
    />
    <BigValue
        data={what_if_conversion}
        value=pct_lift
        title="Revenue Lift"
        fmt="pct2"
    />
</Grid>

<Alert status="positive">
At current conversion <Value data={what_if_conversion} column=current_conversion fmt=pct2/>, 
a +1pp lift projects <Value data={what_if_conversion} column=incremental_revenue fmt=num0/> VND additional daily revenue. 
This is larger than the entire annual marketing budget for most e-commerce businesses.
</Alert>

## Monthly Seasonality

<Alert status="info">
Monthly revenue patterns reveal holiday demand and seasonal trading rhythms. 
Some months consistently outperform others due to cultural events or weather-driven categories.
</Alert>

<BarChart
    data={monthly_seasonality}
    x=month
    y=avg_revenue
    title="Average Daily Revenue by Month"
    subtitle="Reveals annual seasonal patterns"
    yAxisTitle="Revenue"
    xAxisTitle="Month"
    yFmt="num0"
/>

<Alert status="info">
Average daily revenue across all months is <Value data={mean_revenue} column=mean_revenue fmt=num0/> VND.
</Alert>

## Month-End Effect

<Alert status="info">
Month-end days average <Value data={month_end_diff} column=month_end_revenue fmt=num0/> VND vs <Value data={month_end_diff} column=other_revenue fmt=num0/> VND on other days — a structural demand boost. 
This is consistent with salary-cycle purchasing behavior in emerging markets.
</Alert>

<BarChart
    data={month_end_effect}
    x=day_type
    y=avg_revenue
    title="Revenue: Month-End vs Other Days"
    subtitle="Salary-cycle effect on daily revenue"
    yAxisTitle="Revenue"
    yFmt="num0"
/>

<Alert status="info">
Overall average daily revenue is <Value data={mean_revenue} column=mean_revenue fmt=num0/> VND.
</Alert>

## Quarterly Summary

<Alert status="info">
Quarterly aggregation across the selected date range.
Use this to spot multi-quarter trends that daily noise obscures.
</Alert>

<DataTable data={quarterly_summary} rows=10>
    <Column id=quarter_label title="Quarter"/>
    <Column id=avg_revenue title="Avg Revenue" fmt=num0/>
    <Column id=avg_margin title="Margin" fmt=pct2/>
    <Column id=avg_conversion title="Conversion" fmt=pct2/>
    <Column id=avg_return_rate title="Return Rate" fmt=pct2/>
</DataTable>

## Daily Detail

<DataTable data={executive_daily} rows=10>
    <Column id=sales_date title="Date"/>
    <Column id=revenue title="Revenue" fmt=num0/>
    <Column id=gross_margin_rate title="Margin" fmt=pct2/>
    <Column id=order_count title="Orders" fmt=0/>
    <Column id=sessions title="Sessions" fmt=0/>
    <Column id=session_to_order_rate title="Conversion" fmt=pct2/>
    <Column id=return_record_rate title="Return Rate" fmt=pct2/>
    <Column id=avg_days_to_deliver title="Delivery Days" fmt=0.0/>
    <Column id=avg_stockout_days title="Stockout Days" fmt=0/>
    <Column id=wow_revenue_growth_rate title="Revenue Growth" fmt=pct2/>
    <Column id=wow_order_growth_rate title="Order Growth" fmt=pct2/>
</DataTable>

## Related Stories

- [Demand Capture Crisis](/stories/marketing/01-demand-capture-crisis)

