---
title: The Revenue Anatomy
---

# The Revenue Anatomy

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

```sql monthly_revenue_trend
select
    date_trunc('month', sales_date) as month_start,
    sum(revenue) as monthly_revenue,
    sum(order_count) as monthly_orders
from datathon_warehouse.mart_forecast_daily_base
group by 1
order by 1
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

<AreaChart
    data={revenue_cogs_profit_long}
    x=sales_date
    y=value
    series=metric
    title="Revenue, COGS, and Gross Profit Over Time"
    subtitle="Full-period view of top-line scale, cost structure, and margin dollars"
    yAxisTitle="VND"
    yFmt="num0"
/>

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

## 5. Monthly Trajectory

<AreaChart
    data={monthly_revenue_trend}
    x=month_start
    y=monthly_revenue
    title="Monthly Revenue Trend"
    subtitle="Revenue trajectory over the full dataset period"
    yAxisTitle="Revenue (VND)"
    yFmt="num0"
/>

## The Verdict

<Alert status="positive">
<b>Action:</b> Revenue decline is a <b>conversion crisis</b>, not a traffic or pricing crisis. 
Traffic grew <Value data={pct_changes} column=traffic_change fmt=pct2/> but conversion fell <Value data={pct_changes} column=conversion_change fmt=pct2/> — the leak is in the middle of the funnel. 
Organic search is the revenue engine; protect and expand SEO investment. 
The top 20% of customers drive <Value data={customer_concentration} column=top_20_pct fmt=pct2/> of revenue — a VIP retention program is the highest-ROI lever.
</Alert>
