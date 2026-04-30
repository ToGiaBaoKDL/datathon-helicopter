---
title: The 2019 Cliff
---

<Alert status="warning">
<b>The question:</b> In a single year, revenue collapsed 
<b><Value data={annual_cliff} column=revenue_pct_change fmt=pct2/></b>, 
orders fell <b><Value data={annual_cliff} column=orders_pct_change fmt=pct2/></b>, 
and conversion cratered <b><Value data={annual_cliff} column=conversion_pct_change fmt=pct2/></b>.
Traffic actually <b>rose</b>. 
What broke in 2019 — and why did every lever fail at once?
</Alert>

```sql annual_metrics
select
    date_part('year', sales_date)::int as year,
    round(sum(revenue), 0) as revenue,
    sum(order_count) as orders,
    round(avg(session_to_order_rate), 4) as conversion,
    round(avg(sessions), 0) as sessions
from datathon_warehouse.mart_daily_executive_kpis
where sessions > 0
  and date_part('year', sales_date) between 2017 and 2020
group by 1
order by 1
```

```sql annual_cliff
with annual as (
    select
        date_part('year', sales_date)::int as year,
        sum(revenue) as revenue,
        sum(order_count) as orders,
        avg(session_to_order_rate) as conversion,
        avg(sessions) as sessions
    from datathon_warehouse.mart_daily_executive_kpis
    where sessions > 0 and date_part('year', sales_date) in (2018, 2019)
    group by 1
)
select
    round((select revenue from annual where year = 2019) - (select revenue from annual where year = 2018), 0) as revenue_delta,
    round(((select revenue from annual where year = 2019) - (select revenue from annual where year = 2018))::double / (select revenue from annual where year = 2018), 4) as revenue_pct_change,
    round((select orders from annual where year = 2019) - (select orders from annual where year = 2018), 0) as orders_delta,
    round(((select orders from annual where year = 2019) - (select orders from annual where year = 2018))::double / (select orders from annual where year = 2018), 4) as orders_pct_change,
    round((select conversion from annual where year = 2019) - (select conversion from annual where year = 2018), 4) as conversion_delta,
    round(((select conversion from annual where year = 2019) - (select conversion from annual where year = 2018))::double / (select conversion from annual where year = 2018), 4) as conversion_pct_change,
    round((select sessions from annual where year = 2019) - (select sessions from annual where year = 2018), 0) as sessions_delta,
    round(((select sessions from annual where year = 2019) - (select sessions from annual where year = 2018))::double / (select sessions from annual where year = 2018), 4) as sessions_pct_change
from annual
limit 1
```

```sql avg_conversion_2018
select round(avg(session_to_order_rate), 4) as conversion
from datathon_warehouse.mart_daily_executive_kpis
where sessions > 0 and date_part('year', sales_date) = 2018
```

```sql avg_conversion_2019
select round(avg(session_to_order_rate), 4) as conversion
from datathon_warehouse.mart_daily_executive_kpis
where sessions > 0 and date_part('year', sales_date) = 2019
```

```sql avg_sessions_2018
select round(avg(sessions), 0) as sessions
from datathon_warehouse.mart_daily_executive_kpis
where sessions > 0 and date_part('year', sales_date) = 2018
```

```sql monthly_2018_2019
select
    date_trunc('month', sales_date) as month,
    round(sum(revenue), 0) as revenue,
    sum(order_count) as orders,
    round(avg(session_to_order_rate), 4) as conversion,
    round(avg(sessions), 0) as sessions
from datathon_warehouse.mart_daily_executive_kpis
where sessions > 0
  and sales_date between '2018-01-01' and '2019-12-31'
group by 1
order by 1
```

```sql yoy_growth
with monthly as (
    select
        date_trunc('month', sales_date) as month,
        sum(revenue) as revenue
    from datathon_warehouse.mart_daily_executive_kpis
    where sessions > 0
    group by 1
)
select
    month,
    revenue,
    lag(revenue, 12) over (order by month) as revenue_12m_ago,
    round((revenue - lag(revenue, 12) over (order by month))::double
        / nullif(lag(revenue, 12) over (order by month), 0), 4) as yoy_growth_rate
from monthly
where month between '2018-01-01' and '2020-12-31'
order by 1
```

```sql channel_mix
select
    date_part('year', first_order_date)::int as year,
    acquisition_channel,
    count(*) as customers
from datathon_warehouse.mart_customer_rfm
where date_part('year', first_order_date) between 2018 and 2019
group by 1, 2
order by 1, 2
```

```sql payment_mix
select
    date_part('year', sales_date)::int as year,
    case when payment_method = 'cod' then 'COD' else 'Prepaid' end as payment_group,
    sum(order_count) as orders,
    round(sum(revenue), 0) as revenue
from datathon_warehouse.mart_daily_payment_checkout_kpis
where payment_method != 'unknown'
  and date_part('year', sales_date) between 2018 and 2019
group by 1, 2
order by 1, 2
```

```sql return_by_year
select
    date_part('year', sales_date)::int as year,
    round(avg(return_record_rate), 4) as return_record_rate,
    round(avg(return_unit_rate), 4) as return_unit_rate
from datathon_warehouse.mart_daily_returns_kpis
where date_part('year', sales_date) between 2018 and 2019
group by 1
order by 1
```

```sql new_customers_by_year
select
    date_part('year', first_order_date)::int as year,
    count(*) as new_customers
from datathon_warehouse.mart_customer_rfm
where date_part('year', first_order_date) between 2018 and 2019
group by 1
order by 1
```

```sql new_customer_delta
with annual as (
    select
        date_part('year', first_order_date)::int as year,
        count(*) as new_customers
    from datathon_warehouse.mart_customer_rfm
    where year in (2018, 2019)
    group by 1
)
select
    round((select new_customers from annual where year = 2019) - (select new_customers from annual where year = 2018), 0) as customer_delta,
    round(((select new_customers from annual where year = 2019) - (select new_customers from annual where year = 2018))::double / (select new_customers from annual where year = 2018), 4) as customer_pct_change
from (select 1) t
```

```sql inventory_by_year
select
    date_part('year', sales_date)::int as year,
    round(avg(avg_days_of_supply), 0) as days_supply,
    round(avg(stockout_product_count), 0) as stockout_products
from datathon_warehouse.mart_monthly_inventory_snapshot
where date_part('year', sales_date) between 2018 and 2019
group by 1
order by 1
```

```sql inventory_delta
with annual as (
    select
        date_part('year', sales_date)::int as year,
        round(avg(avg_days_of_supply), 0) as days_supply
    from datathon_warehouse.mart_monthly_inventory_snapshot
    where date_part('year', sales_date) in (2018, 2019)
    group by 1
)
select
    round((select days_supply from annual where year = 2019) - (select days_supply from annual where year = 2018), 0) as delta_days,
    round(((select days_supply from annual where year = 2019) - (select days_supply from annual where year = 2018))::double / (select days_supply from annual where year = 2018), 4) as pct_change
from (select 1) t
```

## 0. The Cliff: One Year That Changed Everything

<Alert status="info">
2019 was not a gradual decline — it was a structural break. 
Revenue, orders, and conversion all collapsed simultaneously while traffic grew.
This is not a single-lever failure; it is a system-wide shock.
</Alert>

<Grid cols=4>
    <BigValue
        data={annual_cliff}
        value=revenue_delta
        title="Revenue Drop (VND)"
        fmt="num0"
    />
    <BigValue
        data={annual_cliff}
        value=orders_delta
        title="Orders Lost"
        fmt="0"
    />
    <BigValue
        data={annual_cliff}
        value=conversion_delta
        title="Conversion Drop"
        fmt="pct2"
    />
    <BigValue
        data={annual_cliff}
        value=sessions_delta
        title="Session Change"
        fmt="0"
    />
</Grid>

## 1. Revenue: A <Value data={annual_cliff} column=revenue_pct_change fmt=pct2/> Single-Year Collapse

<Alert status="info">
Annual revenue fell from <Value data={annual_metrics} column=revenue row=1 fmt=num0/> VND in 2018
to <Value data={annual_metrics} column=revenue row=2 fmt=num0/> VND in 2019.
The monthly trajectory shows the decline accelerated through the year —
not a one-off bad quarter, but a sustained downward spiral.
</Alert>

<AreaChart
    data={annual_metrics}
    x=year
    y=revenue
    title="Annual Revenue 2017-2020"
    subtitle="Revenue cliff in 2019 — the steepest single-year drop"
    yAxisTitle="Revenue (VND)"
    yFmt="num0"
>
    <ReferenceArea xMin=2018.5 xMax=2019.5 label="Cliff" color=negative/>
</AreaChart>

<LineChart
    data={monthly_2018_2019}
    x=month
    y=revenue
    title="Monthly Revenue: 2018 vs 2019"
    subtitle="Month-by-month collapse — every month in 2019 underperformed 2018"
    yAxisTitle="Revenue (VND)"
    yFmt="num0"
/>

<BarChart
    data={yoy_growth}
    x=month
    y=yoy_growth_rate
    title="Monthly YoY Revenue Growth"
    subtitle="Negative every month from Jan 2019 — no recovery"
    yAxisTitle="YoY Growth Rate"
    yFmt="pct2"
>
    <ReferenceLine y=0 label="Zero Growth" hideValue=true color=negative lineType=dashed/>
    <ReferenceArea xMin='2019-01-01' xMax='2019-12-31' label="Cliff" color=negative/>
</BarChart>

## 2. Conversion: The Real Killer

<Alert status="info">
Conversion fell from <Value data={annual_metrics} column=conversion row=1 fmt=pct2/> in 2018 
to <Value data={annual_metrics} column=conversion row=2 fmt=pct2/> in 2019 — 
a <Value data={annual_cliff} column=conversion_pct_change fmt=pct2/> drop.
This means the business attracted more visitors but converted far fewer.
The problem was not demand — it was capture.
</Alert>

<LineChart
    data={monthly_2018_2019}
    x=month
    y=conversion
    title="Monthly Conversion Rate: 2018 vs 2019"
    subtitle="Conversion collapsed early 2019 and never recovered"
    yAxisTitle="Conversion Rate"
    yFmt="pct2"
/>

<Alert status="info">
2018 monthly conversion averaged <b><Value data={avg_conversion_2018} column=conversion fmt=pct2/></b>.
2019 monthly conversion averaged <b><Value data={avg_conversion_2019} column=conversion fmt=pct2/></b> —
a <Value data={annual_cliff} column=conversion_pct_change fmt=pct2/> collapse.
</Alert>

## 3. The Traffic Paradox: More Sessions, Less Revenue

<Alert status="info">
Sessions actually <b>rose</b> <Value data={annual_cliff} column=sessions_pct_change fmt=pct2/> in 2019 —
from <Value data={annual_metrics} column=sessions row=1 fmt=0/> to <Value data={annual_metrics} column=sessions row=2 fmt=0/> daily.
But revenue fell <Value data={annual_cliff} column=revenue_pct_change fmt=pct2/>.
This proves the collapse was not a traffic problem — it was a quality, pricing, or product-market-fit crisis.
</Alert>

<AreaChart
    data={monthly_2018_2019}
    x=month
    y=sessions
    title="Monthly Sessions: 2018 vs 2019"
    subtitle="Traffic rose while revenue fell — demand existed but was not captured"
    yAxisTitle="Sessions"
    yFmt="0"
/>

<Alert status="info">
2018 monthly sessions averaged <b><Value data={avg_sessions_2018} column=sessions fmt=0/></b>.
2019 monthly sessions averaged higher — yet conversion collapsed.
</Alert>

<Alert status="info">
The combo chart below overlays orders (bars) on sessions (line) to show the divergence.
When the gap widens, conversion is deteriorating.
</Alert>

```sql sessions_orders_combo
select
    month,
    sessions,
    orders,
    round(orders::double / nullif(sessions, 0), 4) as conversion_rate
from ${monthly_2018_2019}
```

<BarChart
    data={sessions_orders_combo}
    x=month
    y=orders
    y2=sessions
    y2SeriesType=line
    title="Orders (Bars) vs Sessions (Line) — The Divergence"
    subtitle="Widening gap = collapsing conversion. Sessions up, orders down."
    yAxisTitle="Orders"
    y2AxisTitle="Sessions"
    yFmt="0"
    y2Fmt="0"
/>

## 4. Channel Shift: Did Acquisition Quality Change?

<Alert status="info">
If the 2019 collapse was driven by a channel mix shift toward lower-intent traffic,
the composition of new customers should have changed.
</Alert>

<BarChart
    data={channel_mix}
    x=acquisition_channel
    y=customers
    series=year
    title="New Customers by Channel: 2018 vs 2019"
    subtitle="Did acquisition shift toward lower-retention channels?"
    yAxisTitle="Customers"
    yFmt="0"
/>

## 5. Payment Shift: Did COD Surge?

<Alert status="info">
COD orders have higher cancellation rates. 
If the business shifted toward COD in 2019, that would amplify the revenue collapse.
</Alert>

<BarChart
    data={payment_mix}
    x=payment_group
    y=orders
    series=year
    title="Order Volume by Payment Group: 2018 vs 2019"
    subtitle="COD vs Prepaid split — structural shift or cyclical?"
    yAxisTitle="Orders"
    yFmt="0"
/>

## 6. Customer Acquisition: The New-Customer Collapse

<Alert status="info">
New customer acquisition also collapsed in 2019 — 
from <Value data={new_customers_by_year} column=new_customers row=0 fmt=0/> in 2018 
to <Value data={new_customers_by_year} column=new_customers row=1 fmt=0/> in 2019.
That is a <b><Value data={new_customer_delta} column=customer_pct_change fmt=pct2/></b> drop.
The business did not just fail to convert existing traffic — it stopped attracting new buyers.
</Alert>

<BarChart
    data={new_customers_by_year}
    x=year
    y=new_customers
    title="New Customer Count: 2018 vs 2019"
    subtitle="Acquisition collapsed alongside conversion — a double hit"
    yAxisTitle="New Customers"
    yFmt="0"
/>

## 7. Quality & Operations: Exonerated or Complicit?

<Alert status="info">
Return rates stayed flat (<Value data={return_by_year} column=return_record_rate row=0 fmt=pct2/> in 2018
vs <Value data={return_by_year} column=return_record_rate row=1 fmt=pct2/> in 2019) —
quality did not deteriorate. This rules out defective batches as the primary cause.
The 2019 cliff was a <b>demand-capture</b> crisis, not an operational-quality crisis.
</Alert>

<BarChart
    data={return_by_year}
    x=year
    y=return_record_rate
    title="Average Return Record Rate: 2018 vs 2019"
    subtitle="Flat returns rule out quality deterioration as the primary cause"
    yAxisTitle="Return Rate"
    yFmt="pct2"
>
    <ReferenceLine y=0.05 label="5% Alert" hideValue=true color=negative lineType=dashed/>
</BarChart>

<BarChart
    data={inventory_by_year}
    x=year
    y=days_supply
    title="Average Days of Supply: 2018 vs 2019"
    subtitle="Inventory pressure did not spike during the crisis"
    yAxisTitle="Days"
    yFmt="0"
>
    <ReferenceLine y=90 label="90-Day Target" hideValue=true color=positive lineType=dashed/>
</BarChart>

<Alert status="info">
Inventory days of supply averaged <Value data={inventory_by_year} column=days_supply row=0 fmt=0/> in 2018
and <Value data={inventory_by_year} column=days_supply row=1 fmt=0/> in 2019
— a <Value data={inventory_delta} column=pct_change fmt=pct2/> increase.
While inventory rose, it did so gradually and without a sharp inflection matching revenue collapse.
The timing mismatch exonerates supply-chain disruption as the primary cause.
</Alert>

## The Verdict

<Alert status="positive">

<b>Action:</b> 2019 was a <b>structural break</b>, not a gradual decline.
Revenue, orders, conversion, <b>and</b> new customer acquisition all collapsed while traffic rose.
Return rates stayed flat — quality is exonerated. Inventory pressure did not spike — supply chain is exonerated.
The problem was <b>demand capture and acquisition</b>, not product quality or operational failure.
<b>Immediate audit priorities:</b>

- What changed in product assortment or pricing between Q4 2018 and Q1 2019?
- Did a traffic source shift toward low-intent visitors?
- Did a competitor launch or market shift erode product-market fit?
- Did marketing budget cuts reduce new-customer acquisition?
The 2019 baseline is the new normal — recovery must target pre-2019 conversion and acquisition levels, 
not just growth from the 2019 trough.

</Alert>

<Alert status="info">

<b>Cross-reference:</b>

- See <a href="/stories/finance/01-revenue-anatomy">Revenue Anatomy</a> for the full 2013-2022 bridge.
- See <a href="/stories/marketing/01-demand-capture-crisis">Demand Capture Crisis</a> for conversion deep-dive.
- See <a href="/stories/operations/03-risk-flag-convergence">Risk Flag Convergence</a> for operational stress signals.

</Alert>

## Deep Dive

- [Revenue And Drivers](/eda/finance/01-revenue-and-drivers)
- [Seasonal Decomposition](/eda/finance/03-seasonal-decomposition)
- [Executive KPI Pulse](/eda/executive/02-executive-kpi-pulse)
