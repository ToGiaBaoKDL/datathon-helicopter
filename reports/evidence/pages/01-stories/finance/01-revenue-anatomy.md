---
title: The Revenue Anatomy
---

<Alert status="warning">
<b>The question:</b> Revenue fell sharply from 2013 to 2022 despite traffic growing significantly. 
Where did every VND go? Which levers drive revenue, and which are broken?
</Alert>

```sql revenue_bridge
select
    date_part('year', sales_date)::int as year,
    round(avg(sessions), 0) as avg_sessions,
    round(avg(session_to_order_rate), 4) as avg_conversion,
    round(avg(revenue)::double / nullif(avg(order_count), 0), 0) as avg_aov,
    round(avg(revenue), 0) as avg_daily_revenue,
    round(avg(order_count), 0) as avg_orders
from datathon_warehouse.mart_daily_executive_kpis
where sessions > 0 and date_part('year', sales_date) in (2013, 2022)
group by 1
order by 1
```

```sql revenue_by_channel
select
    acquisition_channel,
    round(sum(total_revenue), 0) as total_revenue,
    count(*) as customers,
    round(avg(total_revenue), 0) as avg_ltv
from datathon_warehouse.mart_customer_rfm
group by 1
order by total_revenue desc
```

```sql revenue_by_payment
select
    payment_method,
    round(sum(revenue), 0) as total_revenue,
    sum(order_count) as total_orders
from datathon_warehouse.mart_daily_payment_checkout_kpis
where payment_method != 'unknown'
group by 1
order by total_revenue desc
```

```sql customer_concentration
with ranked as (
    select total_revenue, ntile(5) over (order by total_revenue desc) as quintile
    from datathon_warehouse.mart_customer_rfm
)
select
    round(sum(case when quintile = 1 then total_revenue else 0 end)::double / sum(total_revenue), 4) as top_20_pct,
    round(sum(case when quintile <= 2 then total_revenue else 0 end)::double / sum(total_revenue), 4) as top_40_pct
from ranked
```

```sql pct_changes
select
    round(
        (avg(case when year = 2022 then avg_sessions end) - avg(case when year = 2013 then avg_sessions end))
        / nullif(avg(case when year = 2013 then avg_sessions end), 0),
        4
    ) as traffic_change,
    round(
        (avg(case when year = 2022 then avg_conversion end) - avg(case when year = 2013 then avg_conversion end))
        / nullif(avg(case when year = 2013 then avg_conversion end), 0),
        4
    ) as conversion_change,
    round(
        (avg(case when year = 2022 then avg_aov end) - avg(case when year = 2013 then avg_aov end))
        / nullif(avg(case when year = 2013 then avg_aov end), 0),
        4
    ) as aov_change
from ${revenue_bridge}
```

```sql top_customers
select
    customer_id,
    acquisition_channel,
    round(total_revenue, 0) as total_revenue,
    total_orders,
    round(avg_order_value, 0) as avg_order_value,
    round(recency_days, 0) as recency_days
from datathon_warehouse.mart_customer_rfm
order by total_revenue desc
limit 10
```

```sql monthly_revenue_trend
select
    date_trunc('month', sales_date) as month_start,
    sum(revenue) as monthly_revenue,
    sum(order_count) as monthly_orders
from datathon_warehouse.mart_forecast_daily_base
group by 1
order by 1
```

```sql daily_revenue_calendar
select
    sales_date,
    revenue
from datathon_warehouse.mart_forecast_daily_base
order by sales_date
```

```sql what_if_conversion
select
    round(avg(case when year = 2022 then avg_sessions end), 0) as sessions_2022,
    round(avg(case when year = 2022 then avg_conversion end), 4) as conversion_2022,
    round(avg(case when year = 2013 then avg_conversion end), 4) as conversion_2013,
    round(avg(case when year = 2022 then avg_aov end), 0) as aov_2022,
    round(avg(case when year = 2022 then avg_daily_revenue end), 0) as revenue_2022,
    round(
        avg(case when year = 2022 then avg_sessions end)
        * avg(case when year = 2013 then avg_conversion end)
        * avg(case when year = 2022 then avg_aov end),
        0
    ) as projected_revenue,
    round(
        avg(case when year = 2022 then avg_sessions end)
        * avg(case when year = 2013 then avg_conversion end)
        * avg(case when year = 2022 then avg_aov end)
        - avg(case when year = 2022 then avg_daily_revenue end),
        0
    ) as daily_delta,
    round(
        (avg(case when year = 2022 then avg_sessions end)
         * avg(case when year = 2013 then avg_conversion end)
         * avg(case when year = 2022 then avg_aov end)
         - avg(case when year = 2022 then avg_daily_revenue end)) * 365,
        0
    ) as annual_delta
from ${revenue_bridge}
```

```sql revenue_cogs_profit_long
select sales_date, 'Revenue' as metric, revenue as value
from datathon_warehouse.mart_daily_executive_kpis
union all
select sales_date, 'COGS' as metric, cogs as value
from datathon_warehouse.mart_daily_executive_kpis
union all
select sales_date, 'Gross Profit' as metric, gross_profit as value
from datathon_warehouse.mart_daily_executive_kpis
order by sales_date
```

```sql anomaly_detection
with stats as (
    select
        avg(revenue) as mean_revenue,
        stddev_samp(revenue) as std_revenue
    from datathon_warehouse.mart_daily_executive_kpis
    where sessions > 0
)
select
    e.sales_date,
    e.revenue,
    s.mean_revenue,
    s.std_revenue,
    e.revenue - s.mean_revenue as deviation,
    abs(e.revenue - s.mean_revenue) / nullif(s.std_revenue, 0) as z_score,
    case
        when abs(e.revenue - s.mean_revenue) / nullif(s.std_revenue, 0) > 2 then 'Anomaly'
        else 'Normal'
    end as flag
from datathon_warehouse.mart_daily_executive_kpis e
join stats s on true
where e.sessions > 0
  and abs(e.revenue - s.mean_revenue) / nullif(s.std_revenue, 0) > 2
order by abs(e.revenue - s.mean_revenue) / nullif(s.std_revenue, 0) desc
limit 10
```

```sql yoy_monthly_growth
with monthly as (
    select
        date_trunc('month', sales_date) as month_start,
        sum(revenue) as monthly_revenue
    from datathon_warehouse.mart_daily_executive_kpis
    where sessions > 0
    group by 1
)
select
    month_start,
    monthly_revenue,
    lag(monthly_revenue, 12) over (order by month_start) as revenue_12m_ago,
    round((monthly_revenue - lag(monthly_revenue, 12) over (order by month_start))::double
        / nullif(lag(monthly_revenue, 12) over (order by month_start), 0), 4) as yoy_growth_rate
from monthly
order by month_start
```

```sql daily_revenue_with_ma
select
    sales_date,
    revenue,
    avg(revenue) over (order by sales_date rows between 29 preceding and current row) as ma_30d
from datathon_warehouse.mart_daily_executive_kpis
where sessions > 0
order by sales_date
```

```sql annual_revenue_trend
select
    date_part('year', sales_date)::int as year,
    round(sum(revenue), 0) as annual_revenue
from datathon_warehouse.mart_daily_executive_kpis
where sessions > 0
  and date_part('year', sales_date) between 2017 and 2020
group by 1
order by 1
```

```sql cliff_delta
with annual as (
    select
        date_part('year', sales_date)::int as year,
        sum(revenue) as revenue
    from datathon_warehouse.mart_daily_executive_kpis
    where sessions > 0 and year in (2018, 2019)
    group by 1
)
select
    round((select revenue from annual where year = 2019) - (select revenue from annual where year = 2018), 0) as revenue_drop,
    round(((select revenue from annual where year = 2019) - (select revenue from annual where year = 2018))::double / (select revenue from annual where year = 2018), 4) as revenue_pct_drop
from (select 1) t
```

## 0. Full-Period Revenue Architecture

<Alert status="info">
The chart below shows the full-period trajectory of revenue, COGS, and gross profit.
This establishes the top-line scale before dissecting which levers drive or break it.
</Alert>

<AreaChart
    data={revenue_cogs_profit_long}
    x=sales_date
    y=value
    series=metric
    title="Revenue, COGS, and Gross Profit Over Time"
    subtitle="Full-period view of top-line scale, cost structure, and margin dollars"
    yAxisTitle="VND"
    yFmt="num0"
>
    <ReferenceLine y=0 label="Break-even" hideValue=true color=negative lineType=dashed/>
</AreaChart>

## 1. The Bridge: Four Levers, One Broken

<Alert status="info">
Revenue = Traffic × Conversion × AOV × Frequency. 
From 2013 to 2022: Traffic <b><Value data={pct_changes} column=traffic_change fmt=pct2/></b>, 
Conversion <b><Value data={pct_changes} column=conversion_change fmt=pct2/></b>, 
AOV <b><Value data={pct_changes} column=aov_change fmt=pct2/></b>. 
The collapse is almost entirely a <b>conversion crisis</b>.
</Alert>

<BarChart
    data={revenue_bridge}
    x=year
    y=avg_daily_revenue
    title="Average Daily Revenue: 2013 vs 2022"
    subtitle="Revenue declined despite traffic growth"
    yAxisTitle="Revenue (VND/day)"
    yFmt="num0"
/>

<Grid cols=4>
    <BigValue
        data={revenue_bridge}
        value=avg_sessions
        title="Daily Sessions"
        fmt="0"
    />
    <BigValue
        data={revenue_bridge}
        value=avg_conversion
        title="Conversion Rate"
        fmt="pct2"
    />
    <BigValue
        data={revenue_bridge}
        value=avg_aov
        title="Average Order Value"
        fmt="num0"
    />
    <BigValue
        data={revenue_bridge}
        value=avg_orders
        title="Daily Orders"
        fmt="0"
    />
</Grid>

## 1.5. The 2019 Cliff: Where Revenue Broke

<Alert status="info">
Section 1 shows a conversion crisis spanning 2013–2022. 
But <b>when did the collapse actually begin?</b>
In <b>2019 alone</b>, revenue fell <b><Value data={cliff_delta} column=revenue_pct_drop fmt=pct2/></b> —
from <Value data={annual_revenue_trend} column=annual_revenue row=1 fmt=num0/> VND in 2018 
to <Value data={annual_revenue_trend} column=annual_revenue row=2 fmt=num0/> VND in 2019.
That is <b><Value data={cliff_delta} column=revenue_drop fmt=num0/></b> VND lost in a single year.
2019 was the inflection point; everything after is a new, lower baseline.
</Alert>

<BarChart
    data={annual_revenue_trend}
    x=year
    y=annual_revenue
    title="Annual Revenue 2017-2020"
    subtitle="The 2019 cliff — steeper than any other single-year change"
    yAxisTitle="Revenue (VND)"
    yFmt="num0"
>
    <ReferenceArea xMin=2019 xMax=2019 label="Cliff" color=negative/>
</BarChart>

<BarChart
    data={yoy_monthly_growth}
    x=month_start
    y=yoy_growth_rate
    title="Monthly Revenue YoY Growth"
    subtitle="2019 is the only year with sustained negative YoY months"
    yAxisTitle="YoY Growth Rate"
    yFmt="pct2"
>
    <ReferenceLine y=0 label="Zero Growth" hideValue=true color=negative lineType=dashed/>
    <ReferenceArea xMin='2019-01-01' xMax='2019-12-31' label="Cliff" color=negative/>
</BarChart>

## 2. Channel: Organic Search Is the Revenue Engine

<Alert status="info">
Organic search generates the most absolute revenue — but it also produces the most customers. 
Revenue per customer (LTV) is remarkably uniform across channels.
</Alert>

<BarChart
    data={revenue_by_channel}
    x=acquisition_channel
    y=total_revenue
    title="Total Revenue by Acquisition Channel"
    subtitle="Organic search leads in absolute revenue"
    yAxisTitle="Revenue (VND)"
    yFmt="num0"
/>

<BarChart
    data={revenue_by_channel}
    x=acquisition_channel
    y=avg_ltv
    title="Average LTV by Acquisition Channel"
    subtitle="LTV is uniform — channel choice matters less than volume"
    yAxisTitle="LTV (VND)"
    yFmt="num0"
/>

## 3. Payment: Credit Card Dominates

<Alert status="info">
Credit card drives the majority of revenue. COD is significant but suffers from cancellation leakage.
</Alert>

<BarChart
    data={revenue_by_payment}
    x=payment_method
    y=total_revenue
    title="Total Revenue by Payment Method"
    subtitle="Credit card dominates; COD has volume but leakage"
    yAxisTitle="Revenue (VND)"
    yFmt="num0"
/>

## 4. Concentration: The Pareto Reality

<Alert status="info">
The top 20% of customers generate <b><Value data={customer_concentration} column=top_20_pct fmt=pct2/></b> of total revenue. 
The top 40% generate <b><Value data={customer_concentration} column=top_40_pct fmt=pct2/></b>. 
Revenue is highly concentrated — a small base drives the majority of the business.
</Alert>

<Alert status="info">
The table below shows the top 10 customers by lifetime revenue. 
These are the VIPs that a retention program must protect — losing even one has outsized revenue impact.
</Alert>

<DataTable data={top_customers} rows=10>
    <Column id=customer_id title="Customer ID"/>
    <Column id=acquisition_channel title="Channel"/>
    <Column id=total_revenue title="Revenue" fmt=num0/>
    <Column id=total_orders title="Orders" fmt=0/>
    <Column id=avg_order_value title="AOV" fmt=num0/>
    <Column id=recency_days title="Recency (days)" fmt=0/>
</DataTable>

## 5. Monthly Trajectory

<Alert status="info">
Monthly revenue and order volume together reveal whether growth is price-driven or volume-driven.
When the two series diverge, the cause is either AOV change or product mix shift.
</Alert>

<AreaChart
    data={monthly_revenue_trend}
    x=month_start
    y=monthly_revenue
    title="Monthly Revenue Trend"
    subtitle="Revenue trajectory over the full dataset period"
    yAxisTitle="Revenue (VND)"
    yFmt="num0"
/>

<Alert status="info">
Monthly order count reveals demand capture volume independent of price or mix effects.
Sustained order growth with flat revenue means AOV compression — a pricing or mix problem.
</Alert>

<AreaChart
    data={monthly_revenue_trend}
    x=month_start
    y=monthly_orders
    title="Monthly Order Count"
    subtitle="Order volume trajectory over the full period"
    yAxisTitle="Orders"
    yFmt="0"
/>

<Alert status="info">
The calendar below reveals daily revenue intensity across the entire period.
Bright clusters highlight peak periods; dark stretches reveal troughs.
This granular view makes seasonal patterns and anomaly days immediately visible.
</Alert>

<CalendarHeatmap
    data={daily_revenue_calendar}
    date=sales_date
    value=revenue
    title="Daily Revenue Calendar"
    subtitle="Revenue intensity by day — reveals peak clusters and anomaly periods"
    valueFmt="num0"
/>

## 5.5. Anomaly Detection: Days That Broke the Pattern

<Alert status="info">
Days with revenue more than 2 standard deviations from the mean are flagged as anomalies.
These spikes or drops often coincide with promo events, stockouts, or external shocks.
</Alert>

<DataTable data={anomaly_detection} rows=10>
    <Column id=sales_date title="Date"/>
    <Column id=revenue title="Revenue" fmt=num0/>
    <Column id=mean_revenue title="Mean Revenue" fmt=num0/>
    <Column id=z_score title="Z-Score" fmt=0.00/>
    <Column id=flag title="Flag"/>
</DataTable>

## 5.6. Year-over-Year Monthly Growth

<Alert status="info">
YoY growth strips out seasonality and reveals the true underlying trajectory.
Sustained negative YoY months confirm structural decline, not just seasonal fluctuation.
</Alert>

<BarChart
    data={yoy_monthly_growth}
    x=month_start
    y=yoy_growth_rate
    title="Monthly Revenue YoY Growth Rate"
    subtitle="Year-over-year strips seasonality to reveal true trajectory"
    yAxisTitle="YoY Growth Rate"
    yFmt="pct2"
>
    <ReferenceLine y=0 label="Zero Growth" hideValue=true color=negative lineType=dashed/>
</BarChart>

## 5.7. Daily Revenue with 30-Day Moving Average

<Alert status="info">
The 30-day moving average smooths daily noise and reveals inflection points.
When daily revenue crosses below the MA, it signals a sustained downtrend.
</Alert>

<LineChart
    data={daily_revenue_with_ma}
    x=sales_date
    y=revenue
    title="Daily Revenue with 30-Day Moving Average"
    subtitle="Smooth trend to spot inflection points"
    yAxisTitle="Revenue (VND)"
    yFmt="num0"
/>

## 6. What-If: Restoring 2013 Conversion at 2022 Traffic

<Alert status="info">
At 2022 traffic levels, restoring the 2013 conversion rate would generate
<Value data={what_if_conversion} column=projected_revenue fmt=num0/> VND/day
vs current <Value data={what_if_conversion} column=revenue_2022 fmt=num0/> VND/day.
That is <Value data={what_if_conversion} column=daily_delta fmt=num0/> VND/day left on the table —
or <Value data={what_if_conversion} column=annual_delta fmt=num0/> VND annually.
</Alert>

<Grid cols=3>
    <BigValue
        data={what_if_conversion}
        value=revenue_2022
        title="Current Daily Revenue (2022)"
        fmt="num0"
    />
    <BigValue
        data={what_if_conversion}
        value=projected_revenue
        title="Projected at 2013 Conversion"
        fmt="num0"
    />
    <BigValue
        data={what_if_conversion}
        value=annual_delta
        title="Annual Revenue Gap"
        fmt="num0"
    />
</Grid>

## The Verdict

<Alert status="positive">
<b>Action:</b> Revenue decline is a <b>conversion crisis</b>, not a traffic or pricing crisis.
Traffic grew <Value data={pct_changes} column=traffic_change fmt=pct2/> but conversion fell <Value data={pct_changes} column=conversion_change fmt=pct2/> — the leak is in the middle of the funnel.
Restoring 2013-level conversion at current traffic would add <Value data={what_if_conversion} column=annual_delta fmt=num0/> VND annually.
Organic search is the revenue engine; protect and expand SEO investment.
The top 20% of customers drive <Value data={customer_concentration} column=top_20_pct fmt=pct2/> of revenue — a VIP retention program is the highest-ROI lever.
</Alert>

## Deep Dive

- [Revenue And Drivers](/02-eda/finance/01-revenue-and-drivers)
- [The State of the Business](/01-stories/00-the-state-of-the-business)

