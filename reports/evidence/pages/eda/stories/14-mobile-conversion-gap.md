---
title: The Mobile Conversion Gap
---

# The Mobile Conversion Gap

<Alert status="warning">
<b>The question:</b> Story 01 showed conversion collapsed 73% over a decade. 
Is mobile the primary driver? Desktop and mobile conversion are diverging — and mobile now dominates traffic.
</Alert>

```sql device_conversion
select
    breakdown_value as device_type,
    round(avg(approx_conversion_rate), 4) as avg_conversion,
    round(avg(total_sessions), 0) as avg_sessions,
    round(avg(order_count), 0) as avg_orders,
    round(avg(cancellation_rate), 4) as avg_cancellation_rate
from datathon_warehouse.mart_daily_conversion_breakdown
where breakdown_type = 'device_type'
group by 1
order by avg_conversion desc
```

```sql device_conversion_trend
select
    sales_date,
    breakdown_value as device_type,
    approx_conversion_rate as conversion_rate,
    total_sessions as sessions
from datathon_warehouse.mart_daily_conversion_breakdown
where breakdown_type = 'device_type'
order by sales_date
```

```sql mobile_vs_desktop
select
    round(
        avg(case when breakdown_value = 'mobile' then approx_conversion_rate end), 4
    ) as mobile_conversion,
    round(
        avg(case when breakdown_value = 'desktop' then approx_conversion_rate end), 4
    ) as desktop_conversion,
    round(
        avg(case when breakdown_value = 'mobile' then total_sessions end), 0
    ) as mobile_sessions,
    round(
        avg(case when breakdown_value = 'desktop' then total_sessions end), 0
    ) as desktop_sessions
from datathon_warehouse.mart_daily_conversion_breakdown
where breakdown_type = 'device_type'
```

```sql device_cancel
select
    breakdown_value as device_type,
    round(sum(cancelled_lines)::double / nullif(sum(order_line_count), 0), 4) as cancellation_rate,
    round(avg(avg_order_value), 0) as avg_order_value
from datathon_warehouse.mart_daily_conversion_breakdown
where breakdown_type = 'device_type'
group by 1
order by cancellation_rate desc
```

## 1. The Split: Mobile vs Desktop Conversion

<Alert status="info">
Mobile drives the majority of sessions but converts at a fraction of desktop. 
The gap is the single largest addressable lever in the conversion crisis.
</Alert>

<BarChart
    data={device_conversion}
    x=device_type
    y=avg_conversion
    title="Conversion Rate by Device"
    subtitle="Mobile conversion lags desktop significantly"
    yAxisTitle="Conversion Rate"
    yFmt="pct2"
/>

<BarChart
    data={device_conversion}
    x=device_type
    y=avg_sessions
    title="Average Daily Sessions by Device"
    subtitle="Mobile dominates traffic volume"
    yAxisTitle="Sessions"
    yFmt="0"
/>

## 2. The Trend: Is the Gap Widening?

<Alert status="info">
If mobile conversion is declining while desktop holds steady, the business is losing ground where most customers actually shop.
</Alert>

<LineChart
    data={device_conversion_trend}
    x=sales_date
    y=conversion_rate
    series=device_type
    title="Conversion Rate Trend by Device"
    subtitle="Mobile and desktop conversion trajectories over time"
    yAxisTitle="Conversion Rate"
    yFmt="pct2"
/>

## 3. Mobile Quality: Cancellation and AOV

<Alert status="info">
Mobile does not just convert lower — it may also cancel more or spend less per order. 
These compound the mobile gap into a revenue gap.
</Alert>

<BarChart
    data={device_cancel}
    x=device_type
    y=cancellation_rate
    title="Cancellation Rate by Device"
    subtitle="Mobile checkout friction drives higher cancellation"
    yAxisTitle="Cancellation Rate"
    yFmt="pct2"
/>

<BarChart
    data={device_cancel}
    x=device_type
    y=avg_order_value
    title="Average Order Value by Device"
    subtitle="AOV parity or gap reveals mobile experience quality"
    yAxisTitle="AOV (VND)"
    yFmt="num0"
/>

## The Verdict

<Alert status="positive">
<b>Action:</b> Mobile is the dominant traffic source but the weakest conversion channel. 
Audit mobile checkout flow: simplify forms, enable one-tap payment, reduce page load time. 
If mobile conversion rises to even 50% of desktop, the revenue impact is substantial. 
Mobile UX is no longer a nice-to-have — it is the primary growth lever.
</Alert>
