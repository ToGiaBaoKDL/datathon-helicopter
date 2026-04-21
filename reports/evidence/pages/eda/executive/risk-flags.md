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

```sql risk_summary
select
    sum(stockout_risk_flag) as stockout_risk_days,
    sum(return_spike_flag) as return_spike_days,
    sum(conversion_drop_flag) as conversion_drop_days
from datathon_warehouse.mart_daily_risk_flags
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
```

## Alert Overview

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

<DataTable data={risk_summary} rows=10 />

## Daily Risk Timeline

<LineChart
    data={risk_flags}
    x=sales_date
    y=stockout_risk_flag
    title="Stockout Risk Flag"
    subtitle="1 = day exceeded 90th percentile stockout days"
    yAxisTitle="Flag"
    xAxisTitle="Date"
/>

<LineChart
    data={risk_flags}
    x=sales_date
    y=return_spike_flag
    title="Return Spike Flag"
    subtitle="1 = day exceeded 95th percentile return record rate"
    yAxisTitle="Flag"
    xAxisTitle="Date"
/>

<LineChart
    data={risk_flags}
    x=sales_date
    y=conversion_drop_flag
    title="Conversion Drop Flag"
    subtitle="1 = day below 10th percentile session-to-order rate"
    yAxisTitle="Flag"
    xAxisTitle="Date"
/>

## Daily Detail

<DataTable data={risk_flags} rows=10 />
