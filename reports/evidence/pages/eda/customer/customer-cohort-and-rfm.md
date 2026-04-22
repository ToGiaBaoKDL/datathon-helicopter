---
title: Customer Cohort and RFM
---

# Customer Cohort and RFM

This page tracks customer acquisition quality, retention decay, and lifetime value distribution.

```sql _channels
select distinct acquisition_channel from datathon_warehouse.mart_customer_rfm order by 1
```

```sql _age_groups
select distinct age_group from datathon_warehouse.mart_customer_rfm order by 1
```

<Dropdown
    name=channel_filter
    data={_channels}
    value=acquisition_channel
    multiple=true
    selectAllByDefault=true
    title="Acquisition Channel"
/>

<Dropdown
    name=age_filter
    data={_age_groups}
    value=age_group
    multiple=true
    selectAllByDefault=true
    title="Age Group"
/>

```sql cohort_retention
select
    cohort_month,
    months_since_first_order,
    cohort_size,
    active_customer_count,
    retention_rate,
    total_orders,
    total_revenue,
    avg_order_value
from datathon_warehouse.mart_monthly_customer_cohort
order by cohort_month, months_since_first_order
```

```sql latest_cohort
select *
from datathon_warehouse.mart_monthly_customer_cohort
where months_since_first_order = 0
order by cohort_month desc
limit 1
```

```sql retention_curve
select
    months_since_first_order,
    avg(retention_rate) as avg_retention_rate,
    avg(avg_order_value) as avg_aov
from datathon_warehouse.mart_monthly_customer_cohort
group by 1
order by 1
```

```sql rfm_summary
select
    acquisition_channel,
    age_group,
    count(*) as customers,
    avg(total_orders) as avg_orders,
    avg(total_revenue) as avg_revenue,
    avg(recency_days) as avg_recency,
    avg(avg_days_between_orders) as avg_gap
from datathon_warehouse.mart_customer_rfm
where acquisition_channel in ${inputs.channel_filter.value}
  and age_group in ${inputs.age_filter.value}
group by 1, 2
order by avg_revenue desc
```

```sql clv_tiers
with ranked as (
    select
        customer_id,
        total_revenue,
        total_orders,
        ntile(4) over (order by total_revenue) as revenue_quartile
    from datathon_warehouse.mart_customer_rfm
    where acquisition_channel in ${inputs.channel_filter.value}
      and age_group in ${inputs.age_filter.value}
)
select
    case
        when revenue_quartile = 4 then 'Platinum'
        when revenue_quartile = 3 then 'Gold'
        when revenue_quartile = 2 then 'Silver'
        else 'Bronze'
    end as clv_tier,
    count(*) as customers,
    avg(total_revenue) as avg_revenue,
    avg(total_orders) as avg_orders,
    sum(total_revenue) as tier_revenue,
    sum(total_revenue) * 100.0 / sum(sum(total_revenue)) over () as revenue_share
from ranked
group by revenue_quartile
order by avg_revenue desc
```

```sql churn_risk
select
    case
        when recency_days <= avg_days_between_orders then 'Active'
        when recency_days <= 2 * avg_days_between_orders then 'At Risk'
        else 'Churned'
    end as churn_risk,
    count(*) as customers,
    avg(total_revenue) as avg_revenue,
    avg(recency_days) as avg_recency
from datathon_warehouse.mart_customer_rfm
where acquisition_channel in ${inputs.channel_filter.value}
  and age_group in ${inputs.age_filter.value}
  and avg_days_between_orders is not null
group by churn_risk
order by avg_recency
```

```sql top_customers
select
    customer_id,
    acquisition_channel,
    age_group,
    total_orders,
    total_revenue,
    recency_days,
    avg_days_between_orders as avg_gap
from datathon_warehouse.mart_customer_rfm
where acquisition_channel in ${inputs.channel_filter.value}
  and age_group in ${inputs.age_filter.value}
order by total_revenue desc
limit 10
```

```sql recency_distribution
select
    case
        when recency_days <= 30 then '0-30 days'
        when recency_days <= 90 then '31-90 days'
        when recency_days <= 180 then '91-180 days'
        when recency_days <= 365 then '181-365 days'
        else '365+ days'
    end as recency_bucket,
    count(*) as customers,
    avg(total_revenue) as avg_revenue
from datathon_warehouse.mart_customer_rfm
where acquisition_channel in ${inputs.channel_filter.value}
  and age_group in ${inputs.age_filter.value}
group by 1
order by 1
```

## Latest Cohort Snapshot

<Alert status="info">
The most recent cohort reflects the newest batch of first-time customers. 
Monitor month-0 retention and AOV to spot acquisition quality shifts early.
</Alert>

<BigValue
    data={latest_cohort}
    value=cohort_size
    title="Latest Cohort Size"
/>

<BigValue
    data={latest_cohort}
    value=retention_rate
    fmt="pct"
    title="Month-0 Retention"
/>

<BigValue
    data={latest_cohort}
    value=avg_order_value
    fmt="num0"
    title="Latest Cohort AOV"
/>

## Retention Curve

<Alert status="info">
Retention typically drops sharply in months 1–3, then stabilizes. 
The 20% benchmark line marks a healthy long-term retention threshold for e-commerce.
</Alert>

<LineChart
    data={retention_curve}
    x=months_since_first_order
    y=avg_retention_rate
    title="Average Retention Rate by Cohort Age"
    subtitle="How cohorts decay over time since first order"
    yAxisTitle="Retention Rate"
    xAxisTitle="Months Since First Order"
    yFmt="0.0%"
>
    <ReferenceLine y=0.20 label="20% Benchmark" hideValue=true color=positive/>
</LineChart>

## CLV Tier Distribution

<Alert status="info">
CLV tiers are quartile-based (Platinum = top 25% by revenue). 
Platinum customers typically generate a disproportionate share of total revenue despite being fewer in number.
</Alert>

<Alert status="positive">
Action: Prioritize retention campaigns for Platinum and Gold tiers. 
A 5% churn in Platinum represents a larger revenue loss than a 20% churn in Bronze.
</Alert>

<BarChart
    data={clv_tiers}
    x=clv_tier
    y=customers
    title="Customer Count by CLV Tier"
    subtitle="Quartile-based segmentation by lifetime revenue"
    yAxisTitle="Customers"
    yFmt="num0"
/>

<BarChart
    data={clv_tiers}
    x=clv_tier
    y=revenue_share
    title="Revenue Share by CLV Tier"
    subtitle="Contribution to total revenue (%)"
    yAxisTitle="Revenue Share"
    yFmt="0.0%"
/>

## Churn Risk Segments

<Alert status="warning">
Customers in the "Churned" bucket have not ordered in more than 2× their normal gap. 
These are prime candidates for win-back campaigns.
</Alert>

<BarChart
    data={churn_risk}
    x=churn_risk
    y=customers
    title="Customer Count by Churn Risk"
    subtitle="Based on recency vs. historical ordering gap"
    yAxisTitle="Customers"
    yFmt="num0"
/>

<BarChart
    data={churn_risk}
    x=churn_risk
    y=avg_revenue
    title="Average Lifetime Revenue by Churn Risk"
    subtitle="Revenue at stake in each segment"
    yAxisTitle="Avg Revenue"
    yFmt="num0"
/>

## RFM Segment Overview

<BarChart
    data={rfm_summary}
    x=acquisition_channel
    y=customers
    series=age_group
    title="Customer Count by Acquisition Channel and Age Group"
    subtitle="Segment composition for selected filters"
    yAxisTitle="Customers"
    yFmt="num0"
/>

## Recency Distribution

<BarChart
    data={recency_distribution}
    x=recency_bucket
    y=customers
    title="Customer Recency Distribution"
    subtitle="How recently customers placed their last order"
    yAxisTitle="Customers"
    yFmt="num0"
/>

## Top Customers by Revenue

<DataTable data={top_customers} rows=10 />

## Cohort Detail

<DataTable data={cohort_retention} rows=10 />
