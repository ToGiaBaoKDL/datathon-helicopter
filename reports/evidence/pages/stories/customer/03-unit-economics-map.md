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

## 2. Retention by Channel: Where Customers Stick

<Alert status="info">
Direct customers have the highest M1 retention. Organic search has the lowest. 
The gap is significant: direct customers are nearly <b><Value data={retention_ratio} column=ratio fmt=0.0/>×</b> as likely to return within the first month as organic search customers.
</Alert>

<BarChart
    data={retention_by_channel}
    x=acquisition_channel
    y=m1_retention
    title="Month-1 Retention by Channel"
    subtitle="Direct and referral customers are the stickiest"
    yAxisTitle="M1 Retention Rate"
    yFmt="pct2"
>
    <ReferenceLine y=0.20 label="20% Benchmark" hideValue=true color=positive lineType=dashed/>
</BarChart>

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

## The Verdict

<Alert status="positive">
<b>Action:</b> LTV is uniform across channels, but retention is not.
Shift acquisition budget toward direct and referral (highest retention).
For organic and paid search (lowest retention), invest in first-30-day onboarding to reduce single-order churn.
Volume without retention is a treadmill — optimize for repeat purchase, not just first purchase.
See also <a href="/stories/customer/01-retention-trap">Story 01: The Retention Trap</a> for cohort-level retention dynamics.
</Alert>

## Deep Dive

- [Customer Cohort And Rfm](/eda/customer/01-customer-cohort-and-rfm)

