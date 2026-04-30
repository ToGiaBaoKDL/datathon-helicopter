---
title: The Device Blind Spot
---

<Alert status="warning">
<b>The question:</b> <a href="/stories/marketing/01-demand-capture-crisis">Story 01</a> showed conversion collapsed <Value data={conversion_decline} column=decline_pct fmt=pct2/> over a decade.
Is mobile the culprit? Or does the conversion crisis hit every device equally?
</Alert>

```sql conversion_decline
select
    max(avg_conversion) as peak_conversion,
    min(avg_conversion) as trough_conversion,
    round((min(avg_conversion) - max(avg_conversion)) / nullif(max(avg_conversion), 0), 4) as decline_pct
from (
    select date_part('year', sales_date) as year, avg(session_to_order_rate) as avg_conversion
    from datathon_warehouse.mart_daily_executive_kpis
    where sessions > 0
    group by 1
) t
```

```sql device_conversion
select
    breakdown_value as device_type,
    round(avg(approx_conversion_rate), 4) as avg_conversion,
    round(avg(total_sessions), 0) as avg_sessions,
    round(avg(order_count), 0) as avg_orders,
    cast(sum(cancelled_lines) as double) / nullif(sum(order_line_count), 0) as cancellation_rate,
    cast(sum(revenue) as double) / nullif(sum(order_count), 0) as avg_order_value,
    sum(order_count) as total_orders
from datathon_warehouse.mart_daily_conversion_breakdown
where breakdown_type = 'device_type'
group by 1
order by avg_conversion desc
```

```sql device_conversion_trend
select
    date_trunc('month', sales_date) as month_start,
    breakdown_value as device_type,
    avg(approx_conversion_rate) as avg_conversion_rate
from datathon_warehouse.mart_daily_conversion_breakdown
where breakdown_type = 'device_type'
  and approx_conversion_rate is not null
group by 1, 2
order by 1, 2
```

```sql device_peak_trough
select
    breakdown_value as device_type,
    date_part('year', sales_date)::int as year,
    round(avg(approx_conversion_rate), 4) as avg_conversion
from datathon_warehouse.mart_daily_conversion_breakdown
where breakdown_type = 'device_type'
group by 1, 2
order by 1, 2
```

```sql device_peak
select
    breakdown_value as device_type,
    round(avg(approx_conversion_rate), 4) as peak_conversion
from datathon_warehouse.mart_daily_conversion_breakdown
where breakdown_type = 'device_type'
  and date_part('year', sales_date) = 2013
group by 1
order by peak_conversion desc
```

```sql device_trough
select
    breakdown_value as device_type,
    round(avg(approx_conversion_rate), 4) as trough_conversion
from datathon_warehouse.mart_daily_conversion_breakdown
where breakdown_type = 'device_type'
  and date_part('year', sales_date) = 2021
group by 1
order by trough_conversion desc
```

```sql mobile_vs_desktop
select
    breakdown_value as device_type,
    round(avg(approx_conversion_rate), 4) as avg_conversion,
    round(cast(sum(revenue) as double) / nullif(sum(order_count), 0), 0) as avg_aov,
    sum(order_count) as total_orders
from datathon_warehouse.mart_daily_conversion_breakdown
where breakdown_type = 'device_type'
  and approx_conversion_rate is not null
group by 1
order by avg_conversion desc
```

```sql device_session_share
select
    breakdown_value as device_type,
    round(avg(total_sessions), 0) as avg_sessions,
    round(avg(total_sessions)::double / sum(avg(total_sessions)) over (), 4) as session_share
from datathon_warehouse.mart_daily_conversion_breakdown
where breakdown_type = 'device_type'
group by 1
order by session_share desc
```

```sql tablet_gap
with device_rates as (
    select
        breakdown_value as device_type,
        avg(approx_conversion_rate) as avg_conversion
    from datathon_warehouse.mart_daily_conversion_breakdown
    where breakdown_type = 'device_type'
    group by 1
)
select
    round(
        max(case when device_type = 'tablet' then avg_conversion end)
        / nullif(max(case when device_type = 'mobile' then avg_conversion end), 0),
        1
    ) as tablet_to_mobile_ratio,
    round(max(case when device_type = 'tablet' then avg_conversion end), 4) as tablet_rate,
    round(max(case when device_type = 'mobile' then avg_conversion end), 4) as mobile_rate
from device_rates
```

```sql what_if_tablet
select
    round(avg(total_sessions), 0) as tablet_sessions,
    round(avg(approx_conversion_rate), 4) as tablet_conversion,
    round(avg(revenue), 0) as current_daily_revenue,
    round(avg(total_sessions) * (select mobile_rate from ${tablet_gap}) * (cast(sum(revenue) as double) / nullif(sum(order_count), 0)), 0) as projected_daily_revenue,
    round(avg(total_sessions) * (select mobile_rate from ${tablet_gap}) * (cast(sum(revenue) as double) / nullif(sum(order_count), 0)) - avg(revenue), 0) as delta_revenue
from datathon_warehouse.mart_daily_conversion_breakdown
where breakdown_type = 'device_type'
  and breakdown_value = 'tablet'
```

## 1. Current Conversion by Device

<Alert status="info">
Mobile converts at <b><Value data={mobile_vs_desktop} column=avg_conversion row=0 fmt=pct2/></b> — higher than desktop (<Value data={mobile_vs_desktop} column=avg_conversion row=1 fmt=pct2/>).
The conversion crisis is <b>not</b> mobile-specific. Blaming mobile UX is a distraction.
Tablet is the true laggard at <Value data={tablet_gap} column=tablet_rate fmt=pct2/> — only <Value data={tablet_gap} column=tablet_to_mobile_ratio fmt=0.0/>× the mobile rate.
</Alert>

<BarChart
    data={device_conversion}
    x=device_type
    y=avg_conversion
    title="Average Conversion Rate by Device"
    subtitle="Mobile leads; tablet is the true laggard"
    yAxisTitle="Conversion Rate"
    yFmt="pct2"
>
    <ReferenceLine y=0.005 label="0.5% Target" hideValue=true color=positive lineType=dashed/>
</BarChart>

## 2. The Collapse: Peak (2013) to Trough (2021)

<Alert status="info">
Every device peaked in 2013 and troughed in 2021.
Mobile fell <Value data={device_peak} column=peak_conversion row=0 fmt=pct2/> → <Value data={device_trough} column=trough_conversion row=0 fmt=pct2/>,
desktop <Value data={device_peak} column=peak_conversion row=1 fmt=pct2/> → <Value data={device_trough} column=trough_conversion row=1 fmt=pct2/>,
tablet <Value data={device_peak} column=peak_conversion row=2 fmt=pct2/> → <Value data={device_trough} column=trough_conversion row=2 fmt=pct2/>.
The magnitude of collapse is similar across all devices — a <b>systemic</b> problem.
</Alert>

<BarChart
    data={device_peak}
    x=device_type
    y=peak_conversion
    title="Peak Conversion by Device (2013)"
    subtitle="All devices started strong"
    yAxisTitle="Conversion Rate"
    yFmt="pct2"
/>

<BarChart
    data={device_trough}
    x=device_type
    y=trough_conversion
    title="Trough Conversion by Device (2021)"
    subtitle="All devices ended weak"
    yAxisTitle="Conversion Rate"
    yFmt="pct2"
/>

## 3. Trend Over Time: When Did Each Device Break?

<Alert status="info">
The monthly trend reveals whether the collapse was synchronized across devices or staggered.
If all three lines drop together in 2019, the cause is upstream (traffic quality, pricing, product-market fit).
If one device drops earlier, that device has a unique UX problem.
</Alert>

<LineChart
    data={device_conversion_trend}
    x=month_start
    y=avg_conversion_rate
    series=device_type
    title="Monthly Conversion Rate by Device"
    subtitle="All devices broke together in 2019 — systemic cause, not device-specific"
    yAxisTitle="Conversion Rate"
    yFmt="pct2"
>
    <ReferenceLine y=0.005 label="0.5% Target" hideValue=true color=positive lineType=dashed/>
</LineChart>

## 4. Session Share: Where Traffic Actually Comes From

<Alert status="info">
Device session share reveals whether the business is over-investing in a low-converting channel.
If tablet has high session share but low conversion, that is the biggest lever.
</Alert>

<BarChart
    data={device_session_share}
    x=device_type
    y=session_share
    title="Session Share by Device"
    subtitle="Traffic composition — where visitors come from"
    yAxisTitle="Share of Sessions"
    yFmt="pct2"
/>

## 5. AOV and Cancellation by Device

<Alert status="info">
AOV is uniform across devices, confirming the conversion gap is driven by friction, not price sensitivity.
Cancellation rate varies — higher cancellation on one device signals checkout or trust issues specific to that experience.
</Alert>

<BarChart
    data={device_conversion}
    x=device_type
    y=avg_order_value
    title="Average Order Value by Device"
    subtitle="AOV parity — conversion gap is friction, not price"
    yAxisTitle="AOV (VND)"
    yFmt="num0"
/>

<BarChart
    data={device_conversion}
    x=device_type
    y=cancellation_rate
    title="Cancellation Rate by Device"
    subtitle="Checkout regret by device — where trust breaks"
    yAxisTitle="Cancellation Rate"
    yFmt="pct2"
>
    <ReferenceLine y=0.10 label="10% Alert" hideValue=true color=warning lineType=dashed/>
</BarChart>

## 6. What-If: Tablet Conversion Matched Mobile

<Alert status="info">
Tablet traffic averages <Value data={what_if_tablet} column=tablet_sessions fmt=0/> sessions/day at <Value data={what_if_tablet} column=tablet_conversion fmt=pct2/> conversion.
If tablet converted at the mobile rate (<Value data={tablet_gap} column=mobile_rate fmt=pct2/>),
that would generate <Value data={what_if_tablet} column=projected_daily_revenue fmt=num0/> VND/day
vs current <Value data={what_if_tablet} column=current_daily_revenue fmt=num0/> VND/day.
The delta is <Value data={what_if_tablet} column=delta_revenue fmt=num0/> VND/day left on the table
from tablet UX alone.
</Alert>

<Grid cols=3>
    <BigValue
        data={what_if_tablet}
        value=tablet_sessions
        title="Tablet Daily Sessions"
        fmt="0"
    />
    <BigValue
        data={what_if_tablet}
        value=tablet_conversion
        title="Tablet Conversion"
        fmt="pct2"
    />
    <BigValue
        data={what_if_tablet}
        value=delta_revenue
        title="Daily Revenue Gap"
        fmt="num0"
    />
</Grid>

## The Verdict

<Alert status="positive">
<b>Action:</b> The conversion crisis is <b>systemic</b>, not mobile-specific.
Mobile actually converts better than desktop (<Value data={mobile_vs_desktop} column=avg_conversion row=0 fmt=pct2/> vs <Value data={mobile_vs_desktop} column=avg_conversion row=1 fmt=pct2/>).
The real blind spot is <b>tablet</b> — it converts at only <Value data={tablet_gap} column=tablet_to_mobile_ratio fmt=0.0/>× the mobile rate.
Fix tablet checkout flow and payment-method presentation first.
Stop investing in mobile checkout tweaks and audit product assortment, pricing strategy, and traffic source quality instead.
</Alert>

## Deep Dive

- [Conversion Funnel](/eda/marketing/01-conversion-funnel)
