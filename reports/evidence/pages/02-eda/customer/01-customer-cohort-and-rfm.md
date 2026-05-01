---
title: Customer Cohort and RFM
---

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
    sum(total_revenue) / sum(total_orders) as avg_aov
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
    sum(total_revenue) / sum(sum(total_revenue)) over () as revenue_share
from ranked
group by revenue_quartile
order by avg_revenue desc
```

```sql churn_risk_total
select
    sum(case when recency_days > 2 * avg_days_between_orders then 1 else 0 end) as churned_customers,
    sum(case when avg_days_between_orders is null then 1 else 0 end) as single_order_customers,
    sum(case when recency_days <= avg_days_between_orders then 1 else 0 end) as active_customers,
    sum(case when avg_days_between_orders is not null and recency_days > avg_days_between_orders and recency_days <= 2 * avg_days_between_orders then 1 else 0 end) as at_risk_customers,
    count(*) as total_customers
from datathon_warehouse.mart_customer_rfm
```

```sql churn_risk
select
    case
        when avg_days_between_orders is null then 'Single Order'
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

```sql channel_comparison
select
    acquisition_channel,
    count(*) as customers,
    avg(total_revenue) as avg_revenue,
    avg(total_orders) as avg_orders,
    avg(recency_days) as avg_recency
from datathon_warehouse.mart_customer_rfm
where acquisition_channel in ${inputs.channel_filter.value}
  and age_group in ${inputs.age_filter.value}
group by 1
order by avg_revenue desc
```

```sql cohort_heatmap
select
    date_part('year', cohort_month)::varchar || '-' || lpad(date_part('month', cohort_month)::varchar, 2, '0') as cohort_label,
    months_since_first_order,
    avg(retention_rate) as avg_retention_rate
from datathon_warehouse.mart_cohort_by_channel_age
where months_since_first_order <= 12
  and acquisition_channel in ${inputs.channel_filter.value}
  and age_group in ${inputs.age_filter.value}
group by 1, 2
order by 1, 2
```

```sql retention_by_channel
select
    months_since_first_order,
    acquisition_channel,
    avg(retention_rate) as avg_retention_rate
from datathon_warehouse.mart_cohort_by_channel_age
where months_since_first_order <= 12
  and acquisition_channel in ${inputs.channel_filter.value}
  and age_group in ${inputs.age_filter.value}
group by 1, 2
order by 1, 2
```

```sql retention_by_age
select
    months_since_first_order,
    age_group,
    avg(retention_rate) as avg_retention_rate
from datathon_warehouse.mart_cohort_by_channel_age
where months_since_first_order <= 12
  and acquisition_channel in ${inputs.channel_filter.value}
  and age_group in ${inputs.age_filter.value}
group by 1, 2
order by 1, 2
```

```sql clv_donut
select
    clv_tier as name,
    revenue_share as value
from ${clv_tiers}
```

```sql platinum_share
select revenue_share as pct
from ${clv_tiers}
where clv_tier = 'Platinum'
```

```sql bronze_share
select revenue_share as pct
from ${clv_tiers}
where clv_tier = 'Bronze'
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
    fmt="pct2"
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
Retention drops sharply by month 1, then stabilizes at a low floor. 
This is a classic e-commerce pattern — most customers never return after their first purchase.
</Alert>

<Alert status="warning">
The 20% benchmark is far above actual performance. The realistic target is improving month-1 retention first.
Focus on increasing first-repeat rate rather than long-term retention.
</Alert>

<LineChart
    data={retention_curve}
    x=months_since_first_order
    y=avg_retention_rate
    title="Average Retention Rate by Cohort Age"
    subtitle="Retention drops to ~3.5% by month 1 then flatlines"
    yAxisTitle="Retention Rate"
    xAxisTitle="Months Since First Order"
    yFmt="pct2"
>
    <ReferenceLine y=0.20 label="20% Benchmark" hideValue=true color=positive/>
</LineChart>

## Cohort Retention Heatmap

<Alert status="info">
The cohort heatmap is the classic visualization for retention analysis. 
Each row is a cohort (customers who first ordered in the same month), each column is months since first order.
</Alert>

<Alert status="positive">
<b>How to read:</b> Darker colors = higher retention. Look for rows that fade slower (better cohort quality) 
and columns where all rows stabilize (baseline retention floor).
</Alert>

<Heatmap
    data={cohort_heatmap}
    x=months_since_first_order
    y=cohort_label
    value=avg_retention_rate
    title="Cohort Retention Heatmap"
    subtitle="Retention rate by cohort month and months since first order"
    valueFmt="pct2"
/>

## CLV Tier Distribution

<Alert status="info">
CLV tiers are quartile-based — each tier has ~25% of customers. 
However, <b>Platinum</b> (top 25%) generates <Value data={platinum_share} column=pct fmt=pct2/> of total revenue, 
while <b>Bronze</b> (bottom 25%) contributes only <Value data={bronze_share} column=pct fmt=pct2/>.
Platinum + Gold together represent the majority of revenue — a classic Pareto distribution.
</Alert>

<Alert status="positive">
Action: Prioritize retention for Platinum and Gold. Platinum generates <Value data={platinum_share} column=pct fmt=pct2/> of total revenue — losing 1% of Platinum customers means losing roughly 1% of that share.
</Alert>

<ECharts config={
    {
        tooltip: {
            formatter: '{b}: {c} ({d}%)'
        },
        series: [
            {
                type: 'pie',
                radius: ['40%', '70%'],
                data: [...clv_donut],
            }
        ]
    }
}/>

<BarChart
    data={clv_tiers}
    x=clv_tier
    y=customers
    swapXY=true
    title="Customer Count by CLV Tier"
    subtitle="Each quartile has ~25% of customers — equal count, unequal value"
    yAxisTitle="Customers"
    yFmt="num0"
/>

<BarChart
    data={clv_tiers}
    x=clv_tier
    y=revenue_share
    swapXY=true
    title="Revenue Share by CLV Tier"
    subtitle="Revenue concentration: Platinum dominates despite equal customer count"
    yAxisTitle="Revenue Share"
    yFmt="pct2"
/>

## Churn Risk Segments

<Alert status="info">
<Value data={churn_risk_total} column=churned_customers fmt=num0/> customers are "Churned" — no order in 2× their normal gap. 
<Value data={churn_risk_total} column=single_order_customers fmt=num0/> are "Single Order" — never returned after first purchase. 
These are distinct problems requiring different tactics.
</Alert>

<Alert status="positive">
Action: For Single Order customers, send a "second purchase incentive" within 30 days of first order. 
For Churned customers, use a "we miss you" campaign with personalized product recommendations.
</Alert>

<BarChart
    data={churn_risk}
    x=churn_risk
    y=customers
    swapXY=true
    title="Customer Count by Churn Risk"
    subtitle="Based on recency vs. historical ordering gap"
    yAxisTitle="Customers"
    yFmt="num0"
/>

<BarChart
    data={churn_risk}
    x=churn_risk
    y=avg_revenue
    swapXY=true
    title="Average Lifetime Revenue by Churn Risk"
    subtitle="Revenue at stake in each segment"
    yAxisTitle="Avg Revenue"
    yFmt="num0"
/>

## Retention by Acquisition Channel

<Alert status="info">
Retention quality varies dramatically by acquisition channel. 
<b>Direct</b> and <b>referral</b> customers show markedly higher month-1 retention than <b>organic search</b> and <b>paid search</b>.
This suggests intent quality: customers who seek out the brand directly are more committed than browsers from search ads.
</Alert>

<Alert status="positive">
Action: Shift acquisition budget toward direct and referral programs. 
For paid search, tighten keyword targeting to high-intent terms rather than broad-match browsing keywords.
</Alert>

<LineChart
    data={retention_by_channel}
    x=months_since_first_order
    y=avg_retention_rate
    series=acquisition_channel
    title="Retention Curve by Acquisition Channel"
    subtitle="Month-0 to month-12 retention decay by channel"
    yAxisTitle="Retention Rate"
    xAxisTitle="Months Since First Order"
    yFmt="pct2"
>
    <ReferenceLine y=0.20 label="20% Benchmark" hideValue=true color=positive/>
</LineChart>

## Retention by Age Group

<Alert status="info">
<b>55+ customers</b> have the highest month-1 retention, while <b>25–34</b> is the weakest. 
Older customers are more loyal but represent a smaller segment — the opportunity is improving retention in the largest group (25–34).
</Alert>

<LineChart
    data={retention_by_age}
    x=months_since_first_order
    y=avg_retention_rate
    series=age_group
    title="Retention Curve by Age Group"
    subtitle="Month-0 to month-12 retention decay by age"
    yAxisTitle="Retention Rate"
    xAxisTitle="Months Since First Order"
    yFmt="pct2"
>
    <ReferenceLine y=0.20 label="20% Benchmark" hideValue=true color=positive/>
</LineChart>

## Acquisition Channel Performance

<Alert status="info">
Social media and organic search drive the highest average revenue per customer. 
All channels are remarkably close in performance, suggesting product-market fit is consistent across sources.
</Alert>

<BarChart
    data={channel_comparison}
    x=acquisition_channel
    y=avg_revenue
    swapXY=true
    title="Avg Lifetime Revenue by Channel"
    subtitle="Which acquisition sources bring the highest-value customers"
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
    swapXY=true
    title="Customer Recency Distribution"
    subtitle="How recently customers placed their last order"
    yAxisTitle="Customers"
    yFmt="num0"
/>

## Top Customers by Revenue

<DataTable data={top_customers} rows=10>
    <Column id=customer_id title="Customer"/>
    <Column id=acquisition_channel title="Channel"/>
    <Column id=age_group title="Age"/>
    <Column id=total_orders title="Orders" fmt=0/>
    <Column id=total_revenue title="Revenue" fmt=num0/>
    <Column id=recency_days title="Recency" fmt=0/>
    <Column id=avg_gap title="Avg Gap" fmt=0/>
</DataTable>

## Cohort Detail

<DataTable data={cohort_retention} rows=10>
    <Column id=cohort_month title="Cohort"/>
    <Column id=months_since_first_order title="Months" fmt=0/>
    <Column id=cohort_size title="Cohort Size" fmt=0/>
    <Column id=active_customer_count title="Active" fmt=0/>
    <Column id=retention_rate title="Retention" fmt=pct2/>
    <Column id=total_revenue title="Revenue" fmt=num0/>
    <Column id=avg_order_value title="AOV" fmt=num0/>
</DataTable>

## Related Stories

- [Retention Trap](/01-stories/customer/01-retention-trap)
- [Rfm Who Pays](/01-stories/customer/02-rfm-who-pays)
- [Unit Economics Map](/01-stories/customer/03-unit-economics-map)

