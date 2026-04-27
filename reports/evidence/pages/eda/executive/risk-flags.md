---
title: Risk Flags
---

# Daily Risk Flags

Quick alerts for stockout risk, return spikes, and conversion drops derived from executive KPIs.

```sql _date_bounds
select sales_date from datathon_warehouse.mart_daily_risk_flags
```

<DateRange
    name=date_range
    data={_date_bounds}
    dates=sales_date
/>

```sql risk_flags
select
    sales_date,
    revenue,
    avg_stockout_days,
    return_record_rate,
    session_to_order_rate,
    stockout_risk_flag,
    return_spike_flag,
    conversion_drop_flag
from datathon_warehouse.mart_daily_risk_flags
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
order by sales_date
```

```sql risk_flags_long
select sales_date, 'Stockout Risk' as flag_type, stockout_risk_flag as flag_value
from datathon_warehouse.mart_daily_risk_flags
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
union all
select sales_date, 'Return Spike', return_spike_flag
from datathon_warehouse.mart_daily_risk_flags
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
union all
select sales_date, 'Conversion Drop', conversion_drop_flag
from datathon_warehouse.mart_daily_risk_flags
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
order by sales_date, flag_type
```

```sql risk_summary
select
    sum(stockout_risk_flag) as stockout_risk_days,
    sum(return_spike_flag) as return_spike_days,
    sum(conversion_drop_flag) as conversion_drop_days,
    count(*) as total_days
from datathon_warehouse.mart_daily_risk_flags
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
```

```sql flag_frequency
select
    'Conversion Drop' as flag_type,
    sum(conversion_drop_flag) as flag_count,
    sum(conversion_drop_flag)::double / count(*) as flag_pct
from datathon_warehouse.mart_daily_risk_flags
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
union all
select
    'Return Spike',
    sum(return_spike_flag),
    sum(return_spike_flag)::double / count(*)
from datathon_warehouse.mart_daily_risk_flags
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
union all
select
    'Stockout Risk',
    sum(stockout_risk_flag),
    sum(stockout_risk_flag)::double / count(*)
from datathon_warehouse.mart_daily_risk_flags
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
order by flag_count desc
```

## Alert Overview

<Alert status="info">
Risk flags are derived from dynamic thresholds (quantiles) on executive KPIs. 
A flag = 1 means the day was an extreme outlier — not just a bad day, but a statistically unusual one.
</Alert>

<Alert status="warning">
<b>Conversion drop</b> is the most frequent flag (<Value data={flag_frequency} column=flag_count fmt=0/> days, <Value data={flag_frequency} column=flag_pct fmt=pct2/> of selected period) and the most dangerous. Days below p10 conversion 
are bleeding revenue despite normal traffic. This is a structural problem, not a seasonal blip.
</Alert>

<BigValue
    data={risk_summary}
    value=stockout_risk_days
    title="Stockout Risk Days"
/>

<BigValue
    data={risk_summary}
    value=return_spike_days
    title="Return Spike Days"
/>

<BigValue
    data={risk_summary}
    value=conversion_drop_days
    title="Conversion Drop Days"
/>

## Daily Risk Timeline

<Alert status="info">
Timeline view reveals clustering — multiple flags on consecutive days suggest systemic issues 
(e.g., checkout bug, supplier batch defect) rather than random noise.
</Alert>

<Alert status="positive">
<b>Recommended response by flag type:</b>
<br/>• <b>Stockout risk</b> → Expedite purchase orders for top-moving SKUs; check if spike correlates with promo campaigns.
<br/>• <b>Return spike</b> → Quarantine recent batch from primary supplier; inspect return reason mix for pattern changes.
<br/>• <b>Conversion drop</b> → Check for checkout bugs, payment gateway issues, or page-speed degradation on high-traffic days.
</Alert>

<LineChart
    data={risk_flags_long}
    x=sales_date
    y=flag_value
    series=flag_type
    title="Daily Risk Flags Timeline"
    subtitle="Clustering of flags reveals systemic issues"
    yAxisTitle="Flag (0 = normal, 1 = triggered)"
    xAxisTitle="Date"
    yFmt="0"
>
    <ReferenceLine y=1 label="Triggered" hideValue=true color=negative/>
</LineChart>

## Daily Detail

<DataTable data={risk_flags} rows=10 />
