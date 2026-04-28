---
title: The Retention Trap
---

# The Retention Trap

<Alert status="warning">
<b>The question:</b> One in four customers (<Value data={customer_summary} column=single_pct fmt=pct2/>) buys once and never returns. 
Month-1 retention is <Value data={retention_m1} column=avg_retention fmt=pct2/>.
Why do <Value data={non_returners_m1} column=non_returners_pct fmt=pct2/> of first-time buyers not return within the first month?
</Alert>

```sql customer_summary
select
    count(*) as total_customers,
    sum(case when total_orders = 1 then 1 else 0 end) as single_order_customers,
    round(sum(case when total_orders = 1 then 1 else 0 end)::double / count(*), 3) as single_pct
from datathon_warehouse.mart_customer_rfm
```

```sql retention_curve
select
    months_since_first_order,
    round(avg(retention_rate), 4) as avg_retention
from datathon_warehouse.mart_monthly_customer_cohort
group by 1
order by 1
```

```sql retention_m1
select round(avg(retention_rate), 4) as avg_retention
from datathon_warehouse.mart_monthly_customer_cohort
where months_since_first_order = 1
```

```sql non_returners_m1
select round(1 - avg(retention_rate), 4) as non_returners_pct
from datathon_warehouse.mart_monthly_customer_cohort
where months_since_first_order = 1
```

```sql retention_by_channel
select
    acquisition_channel,
    round(avg(case when months_since_first_order = 1 then retention_rate end), 4) as m1_retention
from datathon_warehouse.mart_cohort_by_channel_age
group by 1
order by m1_retention desc
```

```sql best_channel
select acquisition_channel as best_channel, round(avg(case when months_since_first_order = 1 then retention_rate end), 4) as best_m1
from datathon_warehouse.mart_cohort_by_channel_age
group by 1
order by best_m1 desc
limit 1
```

```sql worst_channel
select acquisition_channel as worst_channel, round(avg(case when months_since_first_order = 1 then retention_rate end), 4) as worst_m1
from datathon_warehouse.mart_cohort_by_channel_age
group by 1
order by worst_m1 asc
limit 1
```

```sql channel_stats
select
    acquisition_channel,
    round(avg(case when months_since_first_order = 1 then retention_rate end), 4) as m1_retention
from datathon_warehouse.mart_cohort_by_channel_age
group by 1
order by m1_retention desc
```

```sql channel_ratio
select
    round(
        (select max(m1_retention) from ${channel_stats})
        / nullif((select min(m1_retention) from ${channel_stats}), 0),
        1
    ) as ratio
```

```sql retention_by_age
select
    age_group,
    round(avg(case when months_since_first_order = 1 then retention_rate end), 4) as m1_retention
from datathon_warehouse.mart_cohort_by_channel_age
group by 1
order by m1_retention desc
```



## 1. The Funnel: One and Done

<Alert status="info">
<Value data={customer_summary} column=single_order_customers fmt=num0/> out of <Value data={customer_summary} column=total_customers fmt=num0/> customers never returned. 
The entire retention problem is the <b>first 30 days</b> — after that, survivors are essentially retained for life.
</Alert>

<Grid cols=3>
    <BigValue
        data={customer_summary}
        value=total_customers
        title="Total Customers"
        fmt="num0"
    />
    <BigValue
        data={customer_summary}
        value=single_order_customers
        title="Single-Order Customers"
        fmt="num0"
    />
    <BigValue
        data={customer_summary}
        value=single_pct
        title="Single-Order Rate"
        fmt="pct2"
    />
</Grid>

## 2. The Curve: A Cliff, Not a Slope

<LineChart
    data={retention_curve}
    x=months_since_first_order
    y=avg_retention
    title="Retention Curve: Month 0 to Month 12"
    subtitle="Retention cliff after month 1 then stagnation"
    yAxisTitle="Retention Rate"
    xAxisTitle="Months Since First Order"
    yFmt="pct2"
>
    <ReferenceLine y=0.20 label="20% Benchmark" hideValue=true color=positive lineType=dashed/>
    <ReferenceLine data={retention_m1} y=avg_retention label="Month-1 Actual" hideValue=true color=negative/>
</LineChart>

## 3. Channel Quality: Intent Drives Loyalty

<Alert status="info">
<b><Value data={best_channel} column=best_channel/></b> customers retain at <Value data={best_channel} column=best_m1 fmt=pct2/> (M1) — 
<b><Value data={channel_ratio} column=ratio fmt=0.0x/></b> the rate of <Value data={worst_channel} column=worst_channel/> (<Value data={worst_channel} column=worst_m1 fmt=pct2/>). 
Intent quality, not volume, drives repeat purchase.
</Alert>

<BarChart
    data={retention_by_channel}
    x=acquisition_channel
    y=m1_retention
    swapXY=true
    title="Month-1 Retention by Acquisition Channel"
    subtitle="Direct and referral customers are twice as loyal as paid search"
    yAxisTitle="Retention Rate"
    yFmt="pct2"
>
    <ReferenceLine y=0.20 label="20% Benchmark" hideValue=true color=positive lineType=dashed/>
</BarChart>

## 4. Age Gap: The Largest Segment Is the Weakest

<BarChart
    data={retention_by_age}
    x=age_group
    y=m1_retention
    swapXY=true
    title="Month-1 Retention by Age Group"
    subtitle="55+ customers are most loyal, but 25–34 (the largest segment) is the weakest"
    yAxisTitle="Retention Rate"
    yFmt="pct2"
/>

## The Verdict

<Alert status="positive">
<b>Action:</b> The entire retention problem is the <b>first 30 days</b>. 
Send a time-limited second-purchase incentive within 30 days of first order. 
Shift acquisition budget toward direct/referral (<Value data={best_channel} column=best_m1 fmt=pct2/> vs <Value data={worst_channel} column=worst_m1 fmt=pct2/> retention). 
For 25–34 (largest, weakest segment), test mobile-first onboarding and social proof.
</Alert>
