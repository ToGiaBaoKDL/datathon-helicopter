---
title: The Device Blind Spot
---

# The Device Blind Spot

<Alert status="warning">
<b>The question:</b> Story 01 showed conversion collapsed 73% over a decade. 
Is mobile the culprit? Or does the conversion crisis hit every device equally?
</Alert>

```sql device_conversion
select
    breakdown_value as device_type,
    round(avg(approx_conversion_rate), 4) as avg_conversion,
    round(avg(total_sessions), 0) as avg_sessions,
    round(avg(order_count), 0) as avg_orders
from datathon_warehouse.mart_daily_conversion_breakdown
where breakdown_type = 'device_type'
group by 1
order by avg_conversion desc
```

```sql device_conversion_trend
select
    sales_date,
    breakdown_value as device_type,
    approx_conversion_rate as conversion_rate
from datathon_warehouse.mart_daily_conversion_breakdown
where breakdown_type = 'device_type'
order by sales_date
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

```sql device_peak_trough
select
    breakdown_value as device_type,
    round(max(approx_conversion_rate), 4) as peak_conversion,
    round(min(approx_conversion_rate), 4) as trough_conversion
from datathon_warehouse.mart_daily_conversion_breakdown
where breakdown_type = 'device_type'
group by 1
order by peak_conversion desc
```

## 1. The Surprise: Mobile Converts Best

<Alert status="info">
Mobile conversion (<Value data={device_conversion} column=avg_conversion row=0 fmt=pct2/>) is actually higher than desktop (<Value data={device_conversion} column=avg_conversion row=1 fmt=pct2/>). 
Tablet is the weakest (<Value data={device_conversion} column=avg_conversion row=2 fmt=pct2/>). 
The conversion crisis is not a mobile UX problem — it is universal.
</Alert>

<BarChart
    data={device_conversion}
    x=device_type
    y=avg_conversion
    title="Conversion Rate by Device"
    subtitle="Mobile leads; tablet lags. The crisis is not device-specific."
    yAxisTitle="Conversion Rate"
    yFmt="pct2"
/>

## 2. The Trend: All Devices Collapsed Together

<Alert status="info">
If the conversion crisis were mobile-driven, mobile would diverge from desktop over time. 
Instead, all three devices track each other closely — the decline is systemic.
</Alert>

<LineChart
    data={device_conversion_trend}
    x=sales_date
    y=conversion_rate
    series=device_type
    title="Conversion Rate Trend by Device"
    subtitle="All devices decline in parallel — a systemic issue, not a mobile issue"
    yAxisTitle="Conversion Rate"
    yFmt="pct2"
/>

## 3. The Uniformity: Cancellation and AOV Are Identical

<Alert status="info">
Cancellation rates and AOV are nearly identical across devices. 
The problem is upstream — traffic quality, product-market fit, or pricing — not downstream checkout friction.
</Alert>

<BarChart
    data={device_cancel}
    x=device_type
    y=cancellation_rate
    title="Cancellation Rate by Device"
    subtitle="Cancellation is uniform — checkout friction is not the differentiator"
    yAxisTitle="Cancellation Rate"
    yFmt="pct2"
/>

<BarChart
    data={device_cancel}
    x=device_type
    y=avg_order_value
    title="Average Order Value by Device"
    subtitle="AOV parity across devices — purchasing power is not the issue"
    yAxisTitle="AOV (VND)"
    yFmt="num0"
/>

## 4. The Collapse: Peak to Trough by Device

<Alert status="info">
Every device peaked in 2013 and troughed in 2021. 
The magnitude of collapse is similar: mobile fell <Value data={device_peak_trough} column=peak_conversion row=0 fmt=pct2/> → <Value data={device_peak_trough} column=trough_conversion row=0 fmt=pct2/>, 
desktop <Value data={device_peak_trough} column=peak_conversion row=1 fmt=pct2/> → <Value data={device_peak_trough} column=trough_conversion row=1 fmt=pct2/>.
</Alert>

<BarChart
    data={device_peak_trough}
    x=device_type
    y=peak_conversion
    title="Peak Conversion by Device (2013)"
    subtitle="All devices started strong"
    yAxisTitle="Conversion Rate"
    yFmt="pct2"
/>

<BarChart
    data={device_peak_trough}
    x=device_type
    y=trough_conversion
    title="Trough Conversion by Device (2021)"
    subtitle="All devices ended weak"
    yAxisTitle="Conversion Rate"
    yFmt="pct2"
/>

## The Verdict

<Alert status="positive">
<b>Action:</b> The conversion crisis is systemic, not mobile-specific. 
Mobile actually converts better than desktop. Blaming mobile UX is a distraction. 
The real culprits are upstream: product-market fit erosion, pricing power loss, or traffic quality decline (see Story 01). 
Stop investing in mobile checkout tweaks and audit product assortment, pricing strategy, and traffic source quality instead.
</Alert>
