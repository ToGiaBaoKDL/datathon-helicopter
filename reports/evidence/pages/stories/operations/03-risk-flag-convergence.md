---
title: The Risk Flag Convergence
---

<Alert status="warning">
<b>The question:</b> Stockout risk, return spikes, and conversion drops sometimes fire on the same day. 
When multiple warning flags converge, the business is in triple jeopardy. How often does this happen?
</Alert>

```sql risk_overview
select
    round(avg(stockout_risk_flag), 4) as stockout_pct,
    round(avg(return_spike_flag), 4) as return_pct,
    round(avg(conversion_drop_flag), 4) as conversion_pct,
    round(
        sum(case when stockout_risk_flag = 1 and return_spike_flag = 1 and conversion_drop_flag = 1 then 1 else 0 end)::double
        / count(*),
        4
    ) as triple_flag_pct,
    round(
        sum(case when stockout_risk_flag = 1 and return_spike_flag = 1 then 1 else 0 end)::double
        / count(*),
        4
    ) as stockout_return_pct,
    round(
        sum(case when stockout_risk_flag = 1 and conversion_drop_flag = 1 then 1 else 0 end)::double
        / count(*),
        4
    ) as stockout_conversion_pct,
    round(
        sum(case when return_spike_flag = 1 and conversion_drop_flag = 1 then 1 else 0 end)::double
        / count(*),
        4
    ) as return_conversion_pct
from datathon_warehouse.mart_daily_risk_flags
```

```sql risk_timeline
select
    sales_date,
    stockout_risk_flag,
    return_spike_flag,
    conversion_drop_flag,
    stockout_risk_flag + return_spike_flag + conversion_drop_flag as flag_count
from datathon_warehouse.mart_daily_risk_flags
order by sales_date
```

```sql compound_risk_days
select
    sales_date,
    revenue,
    session_to_order_rate,
    return_record_rate,
    avg_stockout_days,
    stockout_risk_flag + return_spike_flag + conversion_drop_flag as flag_count
from datathon_warehouse.mart_daily_risk_flags
where stockout_risk_flag + return_spike_flag + conversion_drop_flag >= 2
order by sales_date
```

```sql flag_by_year
select
    date_part('year', sales_date)::int as year,
    round(avg(stockout_risk_flag), 4) as stockout_rate,
    round(avg(return_spike_flag), 4) as return_rate,
    round(avg(conversion_drop_flag), 4) as conversion_rate,
    round(
        sum(case when stockout_risk_flag + return_spike_flag + conversion_drop_flag >= 2 then 1 else 0 end)::double
        / count(*),
        4
    ) as compound_rate
from datathon_warehouse.mart_daily_risk_flags
group by 1
order by 1
```

```sql what_if_risk_reduction
with compound as (
    select avg(revenue) as compound_revenue, count(*) as compound_days
    from datathon_warehouse.mart_daily_risk_flags
    where stockout_risk_flag + return_spike_flag + conversion_drop_flag >= 2
),
normal as (
    select avg(revenue) as normal_revenue
    from datathon_warehouse.mart_daily_risk_flags
    where stockout_risk_flag + return_spike_flag + conversion_drop_flag < 2
)
select
    round(c.compound_revenue, 0) as compound_revenue,
    round(n.normal_revenue, 0) as normal_revenue,
    c.compound_days,
    round(n.normal_revenue - c.compound_revenue, 0) as daily_revenue_gap,
    round(daily_revenue_gap * c.compound_days * 0.5, 0) as half_reduction_lift
from compound c, normal n
```

## 1. The Baseline: How Often Each Flag Fires

<Alert status="info">
<Value data={risk_overview} column=stockout_pct fmt=pct2/> of days hit stockout risk. 
<Value data={risk_overview} column=return_pct fmt=pct2/> hit return spikes. 
<Value data={risk_overview} column=conversion_pct fmt=pct2/> hit conversion drops.
The convergence rate — 2+ flags on the same day — is the critical metric.
</Alert>

<Grid cols=3>
    <BigValue
        data={risk_overview}
        value=stockout_return_pct
        title="Stockout + Return Same Day"
        fmt="pct2"
    />
    <BigValue
        data={risk_overview}
        value=stockout_conversion_pct
        title="Stockout + Conversion Drop Same Day"
        fmt="pct2"
    />
    <BigValue
        data={risk_overview}
        value=return_conversion_pct
        title="Return + Conversion Drop Same Day"
        fmt="pct2"
    />
</Grid>

## 2. The Timeline: When Flags Cluster

<Alert status="info">
Triple-flag days (all 3 firing) are rare but devastating. 
Dual-flag days are more common and still signal operational stress.
</Alert>

<LineChart
    data={risk_timeline}
    x=sales_date
    y=flag_count
    title="Daily Risk Flag Count Over Time"
    subtitle="Days with 2 or 3 flags are compound risk events"
    yAxisTitle="Number of Flags"
    yFmt="0"
/>

## 3. Compound Risk Days: What Happens to Revenue?

<Alert status="info">
On days with 2+ flags, revenue and conversion suffer simultaneously. 
These are not independent risks — they amplify each other.
</Alert>

<DataTable
    data={compound_risk_days}
    rows=10
>
    <Column id=sales_date title="Date"/>
    <Column id=flag_count title="Flags" fmt=0/>
    <Column id=revenue title="Revenue" fmt=num0/>
    <Column id=session_to_order_rate title="Conversion" fmt=pct2/>
    <Column id=return_record_rate title="Return Rate" fmt=pct2/>
</DataTable>

## 4. Annual Trend: Are Risks Intensifying?

<Alert status="info">
The compound risk rate (days with 2+ simultaneous flags) has fluctuated over the years 
but remains structurally present. This is not a one-off anomaly — it is a built-in feature of the business model.
</Alert>

<BarChart
    data={flag_by_year}
    x=year
    y=compound_rate
    title="Compound Risk Rate by Year"
    subtitle="Share of days with 2+ simultaneous risk flags"
    yAxisTitle="Compound Risk Rate"
    yFmt="pct2"
/>

## 5. What-If: Halving Compound-Risk Days

<Alert status="info">
On compound-risk days (2+ flags), revenue averages <b><Value data={what_if_risk_reduction} column=compound_revenue fmt=num0/></b> VND.
On normal days: <b><Value data={what_if_risk_reduction} column=normal_revenue fmt=num0/></b> VND —
a gap of <b><Value data={what_if_risk_reduction} column=daily_revenue_gap fmt=num0/></b> VND per day.
There are <Value data={what_if_risk_reduction} column=compound_days fmt=0/> compound-risk days in total.
If operational improvements halve these days, the revenue protected is <b><Value data={what_if_risk_reduction} column=half_reduction_lift fmt=num0/></b> VND.
</Alert>

<Grid cols=3>
    <BigValue
        data={what_if_risk_reduction}
        value=compound_revenue
        title="Compound-Day Revenue"
        fmt="num0"
    />
    <BigValue
        data={what_if_risk_reduction}
        value=normal_revenue
        title="Normal-Day Revenue"
        fmt="num0"
    />
    <BigValue
        data={what_if_risk_reduction}
        value=half_reduction_lift
        title="Revenue Protected (50% Cut)"
        fmt="num0"
    />
</Grid>

## The Verdict

<Alert status="positive">
<b>Action:</b> Build a compound risk dashboard. 
A day with stockout + conversion drop is a supply-and-demand double hit — pause marketing spend and expedite replenishment. 
A day with return spike + conversion drop is a quality crisis — trigger QC review and customer service surge capacity. 
Triple-flag days warrant an all-hands operational review.
</Alert>

## Deep Dive

- [Risk Flags](/eda/executive/03-risk-flags)

