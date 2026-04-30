---
title: The Unit Economics Map
---

<Alert status="warning">
<b>The question:</b> Not all customers are created equal.
Which acquisition channel produces the highest lifetime value?
And which channel produces customers who disappear after one purchase?
</Alert>

```sql ltv_by_channel
select
    acquisition_channel,
    round(sum(total_revenue), 0) as total_revenue,
    count(*) as customers,
    round(avg(total_revenue), 0) as avg_ltv,
    round(avg(total_orders), 1) as avg_orders,
    round(sum(case when total_orders = 1 then 1 else 0 end)::double / count(*), 4) as single_order_rate
from datathon_warehouse.mart_customer_rfm
group by 1
order by avg_ltv desc
```

```sql retention_by_channel
select
    acquisition_channel,
    round(avg(case when months_since_first_order = 1 then retention_rate end), 4) as m1_retention,
    round(avg(case when months_since_first_order = 6 then retention_rate end), 4) as m6_retention
from datathon_warehouse.mart_cohort_by_channel_age
group by 1
order by m1_retention desc
```

```sql retention_ratio
select
    round(
        max(m1_retention) / nullif(min(m1_retention), 0),
        1
    ) as ratio
from ${retention_by_channel}
```

```sql channel_quality_score
select
    acquisition_channel,
    round(avg(total_revenue), 0) as avg_ltv,
    round(sum(case when total_orders = 1 then 1 else 0 end)::double / count(*), 4) as single_order_rate
from datathon_warehouse.mart_customer_rfm
group by 1
order by avg_ltv desc
```

```sql ltv_retention_scatter
with cohort_by_channel as (
    select
        acquisition_channel,
        avg(case when months_since_first_order = 1 then retention_rate end) as m1_retention
    from datathon_warehouse.mart_cohort_by_channel_age
    group by 1
)
select
    c.acquisition_channel,
    round(avg(c.total_revenue), 0) as avg_ltv,
    round(m.m1_retention, 4) as m1_retention,
    count(*) as customers
from datathon_warehouse.mart_customer_rfm c
left join cohort_by_channel m
    on c.acquisition_channel = m.acquisition_channel
group by 1, m.m1_retention
order by avg_ltv desc
```

```sql channel_efficiency
with cohort_by_channel as (
    select
        acquisition_channel,
        avg(case when months_since_first_order = 1 then retention_rate end) as m1_retention
    from datathon_warehouse.mart_cohort_by_channel_age
    group by 1
)
select
    c.acquisition_channel,
    round(avg(c.total_revenue), 0) as avg_ltv,
    round(m.m1_retention, 4) as m1_retention,
    round(sum(case when c.total_orders = 1 then 1 else 0 end)::double / count(*), 4) as single_order_rate,
    round(avg(c.total_revenue) * m.m1_retention * (1 - sum(case when c.total_orders = 1 then 1 else 0 end)::double / count(*)), 0) as efficiency_score,
    count(*) as customers
from datathon_warehouse.mart_customer_rfm c
left join cohort_by_channel m
    on c.acquisition_channel = m.acquisition_channel
group by 1, m.m1_retention
order by efficiency_score desc
```

```sql channel_concentration
select
    acquisition_channel,
    round(sum(total_revenue), 0) as total_revenue,
    round(sum(total_revenue)::double / (select sum(total_revenue) from datathon_warehouse.mart_customer_rfm), 4) as revenue_share,
    count(*) as customers,
    round(count(*)::double / (select count(*) from datathon_warehouse.mart_customer_rfm), 4) as customer_share
from datathon_warehouse.mart_customer_rfm
group by 1
order by revenue_share desc
```

```sql organic_share
select
    round(sum(total_revenue)::double / (select sum(total_revenue) from datathon_warehouse.mart_customer_rfm), 4) as revenue_share,
    round(count(*)::double / (select count(*) from datathon_warehouse.mart_customer_rfm), 4) as customer_share
from datathon_warehouse.mart_customer_rfm
where acquisition_channel = 'organic_search'
```

```sql direct_share
select
    round(sum(total_revenue)::double / (select sum(total_revenue) from datathon_warehouse.mart_customer_rfm), 4) as revenue_share,
    round(count(*)::double / (select count(*) from datathon_warehouse.mart_customer_rfm), 4) as customer_share
from datathon_warehouse.mart_customer_rfm
where acquisition_channel = 'direct'
```

```sql what_if_shift
with base as (
    select
        acquisition_channel,
        count(*) as customers,
        round(avg(total_revenue), 0) as avg_ltv,
        round(sum(case when total_orders = 1 then 1 else 0 end)::double / count(*), 4) as single_order_rate
    from datathon_warehouse.mart_customer_rfm
    group by 1
),
worst as (
    select avg_ltv, single_order_rate
    from base
    order by single_order_rate desc
    limit 1
),
best as (
    select avg_ltv, single_order_rate
    from base
    order by single_order_rate asc
    limit 1
),
total as (
    select sum(customers) as total_customers from base
)
select
    round(w.avg_ltv, 0) as worst_ltv,
    round(w.single_order_rate, 4) as worst_churn,
    round(b.avg_ltv, 0) as best_ltv,
    round(b.single_order_rate, 4) as best_churn,
    t.total_customers,
    round(t.total_customers * 0.10, 0) as shifted_customers,
    round(shifted_customers * (b.avg_ltv - w.avg_ltv), 0) as ltv_lift
from worst w, best b, total t
```

## 1. LTV by Channel: Nearly Uniform

<Alert status="info">
Lifetime value is remarkably uniform across channels — the spread from highest to lowest is minimal.
Volume, not quality, differentiates channels.
</Alert>

<BarChart
    data={ltv_by_channel}
    x=acquisition_channel
    y=avg_ltv
    title="Average LTV by Acquisition Channel"
    subtitle="LTV is uniform — channel volume matters more than quality"
    yAxisTitle="LTV (VND)"
    yFmt="num0"
/>

## 1.5. Channel Efficiency Score: The Composite Ranking

<Alert status="info">
LTV alone is misleading — a channel with high LTV but low retention is a leaky bucket.
The efficiency score = LTV × M1 retention × (1 − single-order rate).
It ranks channels by <b>net value delivered per customer</b>, not just spend.
</Alert>

<BarChart
    data={channel_efficiency}
    x=acquisition_channel
    y=efficiency_score
    title="Channel Efficiency Score"
    subtitle="LTV × retention × loyalty — net value per customer"
    yAxisTitle="Efficiency Score"
    yFmt="num0"
/>

<Alert status="info">
Direct leads on efficiency score with only <b><Value data={direct_share} column=customer_share fmt=pct2/></b> of total customers — the smallest channel by volume.
Organic search drives the most revenue (<b><Value data={organic_share} column=revenue_share fmt=pct2/></b>) but ranks last on efficiency —
it brings volume, not value. This is the central tension of the unit economics map.
</Alert>

## 2. Retention by Channel

<Alert status="info">
Retention validates the efficiency score. Direct customers are nearly <b><Value data={retention_ratio} column=ratio fmt=0.0/>×</b> as likely to return as organic search customers.
See <a href="/stories/customer/01-retention-trap">Story 01: The Retention Trap</a> for full cohort analysis.
</Alert>

<BarChart
    data={retention_by_channel}
    x=acquisition_channel
    y=m1_retention
    title="Month-1 Retention by Channel"
    subtitle="Retention validates the efficiency ranking"
    yAxisTitle="M1 Retention Rate"
    yFmt="pct2"
>
    <ReferenceLine y=0.10 label="10% Benchmark" hideValue=true color=positive lineType=dashed/>
</BarChart>

## 2.5. LTV vs Retention: The Efficiency Frontier

<Alert status="info">
The scatter below maps every channel by LTV (x) and retention (y). Bubble size = customer count.
Top-right = high LTV + high retention = ideal channel. Bottom-left = low LTV + low retention = avoid.
</Alert>

<BubbleChart
    data={ltv_retention_scatter}
    x=avg_ltv
    y=m1_retention
    series=acquisition_channel
    size=customers
    title="LTV vs Retention by Channel"
    subtitle="Top-right = ideal. Bottom-left = churn trap."
    xAxisTitle="Average LTV (VND)"
    yAxisTitle="M1 Retention Rate"
    xFmt="num0"
    yFmt="pct2"
>
    <ReferenceLine y=0.10 label="10% Benchmark" hideValue=true color=positive lineType=dashed/>
</BubbleChart>

```sql ltv_channel_age
select
    acquisition_channel,
    age_group,
    round(avg(total_revenue), 0) as avg_ltv
from datathon_warehouse.mart_customer_rfm
group by 1, 2
order by 1, 2
```

<Alert status="info">
The heatmap below reveals whether certain channel + age combinations produce higher LTV than others.
Dark cells = high LTV. If one channel dominates a specific age group, that is a targeting opportunity.
</Alert>

<Heatmap
    data={ltv_channel_age}
    x=age_group
    y=acquisition_channel
    value=avg_ltv
    title="Average LTV by Channel and Age Group"
    subtitle="Channel-quality patterns across age segments"
    valueFmt="num0"
/>

## 2.7. Channel Concentration Risk: Revenue Dependency

<Alert status="warning">
<b>Organic search drives <Value data={organic_share} column=revenue_share fmt=pct2/> of total lifetime revenue</b> but ranks last on efficiency score.
If organic search traffic declines (algorithm change, competitor SEO, ad platform policy shift),
the revenue impact is disproportionate. Diversification toward high-efficiency channels (Direct, Referral)
is a risk-mitigation strategy, not just a growth tactic.
</Alert>

<BarChart
    data={channel_concentration}
    x=acquisition_channel
    y=revenue_share
    title="Revenue Share by Channel"
    subtitle="Top channel = 30% of revenue — concentration risk"
    yAxisTitle="Share of Total Revenue"
    yFmt="pct2"
>
    <ReferenceLine y=0.20 label="20% Diversified" hideValue=true color=positive lineType=dashed/>
</BarChart>

<BarChart
    data={channel_concentration}
    x=acquisition_channel
    y=customer_share
    title="Customer Share by Channel"
    subtitle="Customer mix vs revenue mix — mismatch signals inefficiency"
    yAxisTitle="Share of Total Customers"
    yFmt="pct2"
>
    <ReferenceLine y=0.20 label="20% Diversified" hideValue=true color=positive lineType=dashed/>
</BarChart>

## 3. The One-and-Done Problem

<Alert status="info">
Single-order rate varies by channel. Channels with high single-order rates produce customers who never return — wasting acquisition spend.
</Alert>

<BarChart
    data={ltv_by_channel}
    x=acquisition_channel
    y=single_order_rate
    title="Single-Order Rate by Channel"
    subtitle="High single-order rate = low loyalty despite high volume"
    yAxisTitle="Single-Order Rate"
    yFmt="pct2"
/>

## 4. What-If: Shift 10% from Worst to Best Channel

<Alert status="info">
The worst channel (highest single-order rate = <Value data={what_if_shift} column=worst_churn fmt=pct2/>)
produces customers worth <Value data={what_if_shift} column=worst_ltv fmt=num0/> VND on average.
The best channel (lowest single-order rate = <Value data={what_if_shift} column=best_churn fmt=pct2/>)
produces <Value data={what_if_shift} column=best_ltv fmt=num0/> VND.
If 10% of customers (<Value data={what_if_shift} column=shifted_customers fmt=0/>) shifted from worst to best channel,
<Value data={what_if_shift} column=ltv_lift fmt=num0/> VND in additional lifetime value would be generated.
</Alert>

<Grid cols=4>
    <BigValue
        data={what_if_shift}
        value=worst_churn
        title="Worst Channel Churn"
        fmt="pct2"
    />
    <BigValue
        data={what_if_shift}
        value=best_churn
        title="Best Channel Churn"
        fmt="pct2"
    />
    <BigValue
        data={what_if_shift}
        value=shifted_customers
        title="Customers Shifted (10%)"
        fmt="0"
    />
    <BigValue
        data={what_if_shift}
        value=ltv_lift
        title="LTV Lift"
        fmt="num0"
    />
</Grid>

## The Verdict

<Alert status="positive">
<b>Action:</b> LTV is uniform across channels, but <b>efficiency is not</b>.
Direct leads the efficiency score (LTV × retention × loyalty) despite being the smallest channel — 
it brings quality customers, not just volume.
Organic search drives <Value data={organic_share} column=revenue_share fmt=pct2/> of revenue but ranks last on efficiency — a concentration risk.
Shift 10–15% of organic/paid search budget toward Direct and Referral.
For organic and paid search (lowest retention), invest in first-30-day onboarding to reduce single-order churn.
Volume without retention is a treadmill — optimize for repeat purchase, not just first purchase.
See also <a href="/stories/customer/01-retention-trap">Story 01: The Retention Trap</a> for cohort-level retention dynamics.
</Alert>

## Deep Dive

- [Customer Cohort And Rfm](/eda/customer/01-customer-cohort-and-rfm)
