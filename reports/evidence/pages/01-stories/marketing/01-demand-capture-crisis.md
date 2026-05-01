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

```sql device_conversion
select
    breakdown_value as device_type,
    avg(approx_conversion_rate) as avg_conversion_rate,
    cast(sum(cancelled_lines) as double) / nullif(sum(order_line_count), 0) as avg_cancellation_rate,
    cast(sum(revenue) as double) / nullif(sum(order_count), 0) as avg_aov,
    sum(order_count) as total_orders
from datathon_warehouse.mart_daily_conversion_breakdown
where breakdown_type = 'device_type'
  and approx_conversion_rate is not null
group by 1
order by avg_conversion_rate desc
```

```sql payment_conversion
select
    breakdown_value as payment_method,
    avg(approx_conversion_rate) as avg_conversion_rate,
    cast(sum(cancelled_lines) as double) / nullif(sum(order_line_count), 0) as avg_cancellation_rate,
    cast(sum(revenue) as double) / nullif(sum(order_count), 0) as avg_aov,
    sum(order_count) as total_orders
from datathon_warehouse.mart_daily_conversion_breakdown
where breakdown_type = 'payment_method'
  and approx_conversion_rate is not null
group by 1
order by avg_conversion_rate desc
```

```sql source_conversion
select
    breakdown_value as order_source,
    avg(approx_conversion_rate) as avg_conversion_rate,
    cast(sum(cancelled_lines) as double) / nullif(sum(order_line_count), 0) as avg_cancellation_rate,
    cast(sum(revenue) as double) / nullif(sum(order_count), 0) as avg_aov,
    sum(order_count) as total_orders
from datathon_warehouse.mart_daily_conversion_breakdown
where breakdown_type = 'order_source'
  and approx_conversion_rate is not null
group by 1
order by avg_conversion_rate desc
```

```sql all_conversion_rates
select 'Device' as dimension_type, device_type as dimension, avg_conversion_rate from ${device_conversion}
union all
select 'Payment', payment_method, avg_conversion_rate from ${payment_conversion}
union all
select 'Source', order_source, avg_conversion_rate from ${source_conversion}
```

```sql all_aov
select 'Device' as dimension_type, device_type as dimension, avg_aov from ${device_conversion}
union all
select 'Payment', payment_method, avg_aov from ${payment_conversion}
union all
select 'Source', order_source, avg_aov from ${source_conversion}
```

```sql cancellation_by_payment
select
    breakdown_value as payment_method,
    cast(sum(cancelled_lines) as double) / nullif(sum(order_line_count), 0) as avg_cancellation_rate,
    sum(cancelled_lines) as total_cancelled_lines,
    sum(order_line_count) as total_lines
from datathon_warehouse.mart_daily_conversion_breakdown
where breakdown_type = 'payment_method'
group by 1
order by avg_cancellation_rate desc
```

```sql payment_conversion_trend
select
    date_trunc('month', sales_date) as month_start,
    breakdown_value as payment_method,
    avg(approx_conversion_rate) as avg_conversion_rate
from datathon_warehouse.mart_daily_conversion_breakdown
where breakdown_type = 'payment_method'
  and approx_conversion_rate is not null
group by 1, 2
order by 1, 2
```

```sql source_conversion_trend
select
    date_trunc('month', sales_date) as month_start,
    breakdown_value as order_source,
    avg(approx_conversion_rate) as avg_conversion_rate
from datathon_warehouse.mart_daily_conversion_breakdown
where breakdown_type = 'order_source'
  and approx_conversion_rate is not null
group by 1, 2
order by 1, 2
```

```sql conversion_2019_cliff
with annual as (
    select
        date_part('year', sales_date)::int as year,
        avg(session_to_order_rate) as avg_conversion
    from datathon_warehouse.mart_daily_executive_kpis
    where sessions > 0 and year in (2018, 2019)
    group by 1
)
select
    round((select avg_conversion from annual where year = 2018), 4) as conversion_2018,
    round((select avg_conversion from annual where year = 2019), 4) as conversion_2019,
    round((select avg_conversion from annual where year = 2019) - (select avg_conversion from annual where year = 2018), 4) as conversion_drop,
    round(((select avg_conversion from annual where year = 2019) - (select avg_conversion from annual where year = 2018))::double / (select avg_conversion from annual where year = 2018), 4) as conversion_pct_drop
from (select 1) t
```

```sql monthly_conversion_2018_2019
select
    date_trunc('month', sales_date) as month,
    round(avg(session_to_order_rate), 4) as conversion
from datathon_warehouse.mart_daily_executive_kpis
where sessions > 0
  and sales_date between '2018-01-01' and '2019-12-31'
group by 1
order by 1
```

```sql monthly_cancellation_2018_2019
select
    date_trunc('month', sales_date) as month,
    round(avg(cancellation_rate), 4) as cancellation_rate
from datathon_warehouse.mart_daily_payment_checkout_kpis
where sales_date between '2018-01-01' and '2019-12-31'
group by 1
order by 1
```

```sql cc_vs_bt
with cc as (
    select avg(approx_conversion_rate) as rate
    from datathon_warehouse.mart_daily_conversion_breakdown
    where breakdown_type = 'payment_method'
      and breakdown_value = 'credit_card'
      and approx_conversion_rate is not null
),
bt as (
    select avg(approx_conversion_rate) as rate
    from datathon_warehouse.mart_daily_conversion_breakdown
    where breakdown_type = 'payment_method'
      and breakdown_value = 'bank_transfer'
      and approx_conversion_rate is not null
)
select
    cc.rate as cc_rate,
    bt.rate as bt_rate,
    round(cc.rate / nullif(bt.rate, 0), 1) as ratio
from cc, bt
```

```sql tablet_rate
select avg(approx_conversion_rate) as tablet_conversion
from datathon_warehouse.mart_daily_conversion_breakdown
where breakdown_type = 'device_type'
  and breakdown_value = 'tablet'
  and approx_conversion_rate is not null
```

```sql overall_aov
select
    round(avg(revenue)::double / nullif(avg(order_count), 0), 0) as avg_aov
from datathon_warehouse.mart_daily_executive_kpis
where sessions > 0
```

```sql cod_cancel_ratio
select
    round(
        max(case when payment_method = 'cod' then avg_cancellation_rate end)
        / nullif(max(case when payment_method != 'cod' then avg_cancellation_rate end), 0),
        1
    ) as ratio
from ${cancellation_by_payment}
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
/>

<Alert status="info">
Peak conversion: <b><Value data={peak_year} column=peak_conversion fmt=pct2/></b> in <Value data={peak_year} column=year/>.
Trough conversion: <b><Value data={trough_year} column=trough_conversion fmt=pct2/></b> in <Value data={trough_year} column=year/>.
</Alert>

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
(2) a tablet UX gap — tablet converts at <Value data={tablet_rate} column=tablet_conversion fmt=pct2/>, roughly one-third the mobile rate — 
or (3) a payment-method friction shift as customers moved from credit card to bank transfer or COD.
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
/>

## 2.5. Conversion by Dimension: Where Demand Leaks

<Alert status="info">
Conversion rate varies dramatically by device, payment method, and traffic source. 
Credit card converts at <b><Value data={cc_vs_bt} column=ratio fmt=0.0/>×</b> the rate of bank transfer 
(<Value data={cc_vs_bt} column=cc_rate fmt=pct2/> vs <Value data={cc_vs_bt} column=bt_rate fmt=pct2/>). 
Organic search outperforms paid search. These gaps are fixable with UX and checkout optimisation.
</Alert>

<BarChart
    data={all_conversion_rates}
    x=dimension
    y=avg_conversion_rate
    series=dimension_type
    title="Conversion Rate by Dimension"
    subtitle="Device, payment, and source — unified comparison"
    yAxisTitle="Conversion Rate"
    yFmt="pct2"
>
    <ReferenceLine y=0.005 label="0.5% Target" hideValue=true color=positive lineType=dashed/>
</BarChart>

## 2.6. Average Order Value by Dimension

<Alert status="info">
AOV is remarkably uniform across dimensions (~<Value data={overall_aov} column=avg_aov fmt=num0/> VND).
This means the conversion gap is not driven by price sensitivity — it is driven by checkout friction, trust, or UX.
</Alert>

<BarChart
    data={all_aov}
    x=dimension
    y=avg_aov
    series=dimension_type
    title="Average Order Value by Dimension"
    subtitle="Spending behaviour is consistent — friction is the differentiator"
    yAxisTitle="AOV (VND)"
    yFmt="num0"
/>

## 2.7. Cancellation Friction by Payment Method

<Alert status="warning">
COD cancellation rate is <b><Value data={cod_cancel_ratio} column=ratio fmt=0.0/>×</b> the non-COD rate.
Customers change their mind before the courier arrives. This is a last-mile logistics waste that erodes margin.
</Alert>

<BarChart
    data={cancellation_by_payment}
    x=payment_method
    y=avg_cancellation_rate
    title="Cancellation Rate by Payment Method"
    subtitle="COD dominates checkout regret"
    yAxisTitle="Cancellation Rate"
    yFmt="pct2"
>
    <ReferenceLine y=0.10 label="10% Alert" hideValue=true color=warning lineType=dashed/>
</BarChart>

## 2.8. Conversion Trend by Payment Method

<Alert status="info">
Monthly conversion trends by payment method reveal which checkout options are degrading over time. 
If credit card conversion drops while COD stays flat, the issue is trust or card-processing friction.
</Alert>

<LineChart
    data={payment_conversion_trend}
    x=month_start
    y=avg_conversion_rate
    series=payment_method
    title="Monthly Conversion Rate by Payment Method"
    subtitle="Track payment-method stability over time"
    yAxisTitle="Conversion Rate"
    yFmt="pct2"
>
    <ReferenceLine y=0.005 label="0.5% Target" hideValue=true color=positive lineType=dashed/>
</LineChart>

## 2.9. Conversion Trend by Traffic Source

<Alert status="info">
Traffic source trends reveal whether the business is buying low-intent clicks. 
If paid search conversion drops while spend stays flat, that is a classic CAC trap.
</Alert>

<LineChart
    data={source_conversion_trend}
    x=month_start
    y=avg_conversion_rate
    series=order_source
    title="Monthly Conversion Rate by Traffic Source"
    subtitle="Which channels are degrading and which are stable"
    yAxisTitle="Conversion Rate"
    yFmt="pct2"
>
    <ReferenceLine y=0.005 label="0.5% Target" hideValue=true color=positive lineType=dashed/>
</LineChart>

## 2.10. The 2019 Inflection Point

<Alert status="info">
Sections 2.5–2.9 show conversion gaps across devices, payments, and sources. 
But <b>when did the entire system break?</b>
In 2019 alone, conversion fell from <b><Value data={conversion_2019_cliff} column=conversion_2018 fmt=pct2/></b> 
to <b><Value data={conversion_2019_cliff} column=conversion_2019 fmt=pct2/></b> — 
a <b><Value data={conversion_2019_cliff} column=conversion_pct_drop fmt=pct2/></b> single-year collapse.
This is not gradual erosion — it is a structural break.
</Alert>

<LineChart
    data={monthly_conversion_2018_2019}
    x=month
    y=conversion
    title="Monthly Conversion Rate: 2018 vs 2019"
    subtitle="Conversion collapsed in early 2019 and stabilized at a new lower baseline"
    yAxisTitle="Conversion Rate"
    yFmt="pct2"
>
    <ReferenceLine y=0.005 label="0.5% Target" hideValue=true color=positive lineType=dashed/>
</LineChart>

<Alert status="info">
Cancellation rate also worsened in 2019, compounding the capture crisis.
More visitors cancelled after initiating checkout — a trust or pricing signal.
</Alert>

<LineChart
    data={monthly_cancellation_2018_2019}
    x=month
    y=cancellation_rate
    title="Monthly Cancellation Rate: 2018 vs 2019"
    subtitle="Checkout regret intensified alongside conversion collapse"
    yAxisTitle="Cancellation Rate"
    yFmt="pct2"
>
    <ReferenceLine y=0.10 label="10% Alert" hideValue=true color=warning lineType=dashed/>
</LineChart>

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

<BarChart
    data={daily_conversion}
    x=sales_date
    y=order_count
    y2=sessions
    y2SeriesType=line
    title="Orders (Bars) vs Sessions (Line) — The Divergence"
    subtitle="Sessions trend up while orders trend down — the capture gap widens"
    yAxisTitle="Orders"
    y2AxisTitle="Sessions"
    yFmt="0"
    y2Fmt="0"
/>

## The Verdict

<Alert status="positive">
<b>Action:</b> This is a demand <b>capture</b> crisis, not a demand <b>generation</b> crisis. 
Traffic is at an all-time high. Conversion is at an all-time low. 
Audit tablet UX, payment-method coverage, and checkout flow friction. 
Restoring 2013-level conversion at current traffic would add <Value data={what_if_scenario} column=annual_delta fmt=num0/> VND annually.
</Alert>

## Deep Dive

- [Conversion Funnel](/02-eda/marketing/01-conversion-funnel)
- [Executive Kpi Pulse](/02-eda/executive/02-executive-kpi-pulse)

