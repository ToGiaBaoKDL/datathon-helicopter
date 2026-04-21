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
