---
title: The Demand Capture Crisis
---

<Alert status="warning">
<b>The question:</b> Revenue fell sharply from peak to 2022, yet daily traffic grew.
Conversion collapsed from <b><Value data={peak_year} column=peak_conversion fmt=pct2/></b> (<Value data={peak_year} column=year/>) to <b><Value data={trough_year} column=trough_conversion fmt=pct2/></b> (<Value data={trough_year} column=year/>).
The business is hemorrhaging demand it already generates.
</Alert>

```sql annual_conversion
select
    date_part('year', sales_date)::int as year,
    round(avg(session_to_order_rate), 4) as avg_conversion,
    round(avg(sessions), 0) as avg_sessions,
    round(avg(revenue), 0) as avg_revenue,
    round(avg(order_count), 0) as avg_orders
from datathon_warehouse.mart_daily_executive_kpis
where sessions > 0
group by 1
order by 1
```

```sql peak_year
select
    date_part('year', sales_date)::int as year,
    round(avg(session_to_order_rate), 4) as peak_conversion
from datathon_warehouse.mart_daily_executive_kpis
where sessions > 0
group by 1
order by avg(session_to_order_rate) desc
limit 1
```

```sql trough_year
select
    date_part('year', sales_date)::int as year,
    round(avg(session_to_order_rate), 4) as trough_conversion
from datathon_warehouse.mart_daily_executive_kpis
where sessions > 0
group by 1
order by avg(session_to_order_rate) asc
limit 1
```

```sql daily_conversion
select
    sales_date,
    session_to_order_rate as conversion_rate,
    sessions,
    order_count,
    revenue
from datathon_warehouse.mart_daily_executive_kpis
where sessions > 0
  and sales_date >= '2013-01-01'
order by sales_date
```

```sql what_if_scenario
select
    round(avg(revenue), 0) as current_revenue,
    round(avg(sessions), 0) as current_sessions,
    round(avg(order_count), 0) as current_orders,
    round(avg(sessions) * (select peak_conversion from ${peak_year}), 0) as projected_orders,
    round(avg(sessions) * (select peak_conversion from ${peak_year}) * (avg(revenue)::double / nullif(avg(order_count), 0)), 0) as projected_revenue,
    round(avg(sessions) * (select peak_conversion from ${peak_year}) * (avg(revenue)::double / nullif(avg(order_count), 0)) - avg(revenue), 0) as delta_revenue,
    round((avg(sessions) * (select peak_conversion from ${peak_year}) * (avg(revenue)::double / nullif(avg(order_count), 0)) - avg(revenue)) * 365, 0) as annual_delta
from datathon_warehouse.mart_daily_executive_kpis
where date_part('year', sales_date) = 2022
```

```sql traffic_growth
select
    round(avg(case when year = 2013 then avg_sessions end), 0) as sessions_2013,
    round(avg(case when year = 2022 then avg_sessions end), 0) as sessions_2022,
    round(avg(case when year = 2013 then avg_orders end), 0) as orders_2013,
    round(avg(case when year = 2022 then avg_orders end), 0) as orders_2022,
    round(
        (avg(case when year = 2022 then avg_sessions end) - avg(case when year = 2013 then avg_sessions end))
        / nullif(avg(case when year = 2013 then avg_sessions end), 0),
        4
    ) as sess_growth_pct,
    round(
        (avg(case when year = 2022 then avg_orders end) - avg(case when year = 2013 then avg_orders end))
        / nullif(avg(case when year = 2013 then avg_orders end), 0),
        4
    ) as orders_change_pct
from ${annual_conversion}
```

```sql conversion_funnel
select 'Sessions' as stage, round(avg(sessions), 0) as value
from datathon_warehouse.mart_forecast_daily_base
union all
select 'Unique Visitors', round(avg(unique_visitors), 0)
from datathon_warehouse.mart_forecast_daily_base
union all
select 'Orders', round(avg(order_count), 0)
from datathon_warehouse.mart_forecast_daily_base
```

```sql funnel_loss
select
    round(
        (select avg(sessions) from datathon_warehouse.mart_forecast_daily_base)
        - (select avg(order_count) from datathon_warehouse.mart_forecast_daily_base),
        0
    ) as lost_sessions,
    round(
        (select avg(order_count) from datathon_warehouse.mart_forecast_daily_base)
        / nullif((select avg(sessions) from datathon_warehouse.mart_forecast_daily_base), 0),
        4
    ) as capture_rate
```

## 1. The Traffic Is There — The Capture Is Not

<Alert status="info">
Sessions grew <b><Value data={traffic_growth} column=sess_growth_pct fmt=pct2/></b> 
(<Value data={traffic_growth} column=sessions_2013 fmt=num0/> → <Value data={traffic_growth} column=sessions_2022 fmt=num0/>). 
Orders fell <b><Value data={traffic_growth} column=orders_change_pct fmt=pct2/></b> 
(<Value data={traffic_growth} column=orders_2013 fmt=num0/> → <Value data={traffic_growth} column=orders_2022 fmt=num0/>). 
The top of the funnel is growing. The bottom is leaking.
</Alert>

<LineChart
    data={daily_conversion}
    x=sales_date
    y=conversion_rate
    title="Conversion Rate: 10-Year Collapse"
    subtitle="From peak to trough — the dominant driver of revenue decline"
    yAxisTitle="Session-to-Order Rate"
    xAxisTitle="Date"
    yFmt="pct2"
>
    <ReferenceLine data={peak_year} y=peak_conversion label="Peak" hideValue=true color=positive lineType=dashed/>
    <ReferenceLine data={trough_year} y=trough_conversion label="Trough" hideValue=true color=negative lineType=dashed/>
</LineChart>

<Alert status="info">
The funnel below shows the average daily flow: <b><Value data={funnel_loss} column=lost_sessions fmt=0/></b> sessions do not convert to orders.
Only <b><Value data={funnel_loss} column=capture_rate fmt=pct2/></b> of sessions result in an order — the rest leak at the capture stage.
</Alert>

<FunnelChart
    data={conversion_funnel}
    nameCol=stage
    valueCol=value
    title="Demand Capture Funnel"
    subtitle="Sessions generate traffic, but only a fraction becomes orders"
    valueFmt="0"
/>

## 2. When It Broke: The 2019 Inflection

<Alert status="info">
<Value data={peak_year} column=year/> = peak conversion (<Value data={peak_year} column=peak_conversion fmt=pct2/>). 
<Value data={trough_year} column=year/> = trough (<Value data={trough_year} column=trough_conversion fmt=pct2/>). 
Between 2018 and 2019, conversion dropped sharply in a single year. 
Three plausible drivers: (1) a traffic source shift toward lower-intent channels, 
(2) a mobile UX degradation that the 2018–2019 period would have magnified, 
or (3) a product mix shift away from high-conversion categories.
</Alert>

<BarChart
    data={annual_conversion}
    x=year
    y=avg_conversion
    title="Annual Average Conversion Rate"
    subtitle="2019 inflection: structural break, not gradual decay"
    yAxisTitle="Conversion Rate"
    xAxisTitle="Year"
    yFmt="pct2"
>
    <ReferenceLine data={peak_year} y=peak_conversion label="Peak" hideValue=true color=positive lineType=dashed/>
</BarChart>

## 3. The Cost: What If Conversion Stayed at Peak?

<Alert status="info">
At 2022 traffic levels, restoring peak conversion would generate 
<Value data={what_if_scenario} column=projected_revenue fmt=num0/> VND/day vs current <Value data={what_if_scenario} column=current_revenue fmt=num0/> VND/day. 
That is <Value data={what_if_scenario} column=delta_revenue fmt=num0/> VND/day left on the table — 
or <Value data={what_if_scenario} column=annual_delta fmt=num0/> VND annually.
</Alert>

<Grid cols=3>
    <BigValue
        data={what_if_scenario}
        value=current_revenue
        title="Current Daily Revenue (2022)"
        fmt="num0"
    />
    <BigValue
        data={what_if_scenario}
        value=projected_revenue
        title="Projected at Peak Conversion"
        fmt="num0"
    />
    <BigValue
        data={what_if_scenario}
        value=delta_revenue
        title="Daily Revenue Gap"
        fmt="num0"
    />
</Grid>

## 4. Sessions vs Orders: Divergence

<Alert status="info">
The divergence between sessions and orders is the visual proof of the capture crisis.
Sessions trend upward (growing traffic investment) while orders trend downward (leaking demand).
The gap between the two lines represents unrealized revenue.
</Alert>

<AreaChart
    data={daily_conversion}
    x=sales_date
    y=sessions
    title="Daily Sessions (Traffic)"
    subtitle="Sessions trend upward while orders decline"
    yAxisTitle="Sessions"
    yFmt="0"
/>

<AreaChart
    data={daily_conversion}
    x=sales_date
    y=order_count
    title="Daily Orders"
    subtitle="Order volume collapses despite growing traffic"
    yAxisTitle="Orders"
    yFmt="0"
/>

## The Verdict

<Alert status="positive">
<b>Action:</b> This is a demand <b>capture</b> crisis, not a demand <b>generation</b> crisis. 
Traffic is at an all-time high. Conversion is at an all-time low. 
Audit mobile UX, page load speed, payment coverage, and checkout flow friction. 
Restoring 2013-level conversion at current traffic would add <Value data={what_if_scenario} column=annual_delta fmt=num0/> VND annually.
</Alert>

## Deep Dive

- [Conversion Funnel](/eda/marketing/01-conversion-funnel)
- [Executive Kpi Pulse](/eda/executive/02-executive-kpi-pulse)

