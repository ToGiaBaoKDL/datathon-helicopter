---
title: Conversion Funnel and Traffic Quality
---

This page breaks down demand capture efficiency by device, traffic source, and payment method. 
It answers: <i>where do shoppers drop off, and which channels actually convert?</i>

```sql _date_bounds
select sales_date from datathon_warehouse.mart_forecast_daily_base
```

```sql _breakdown_types
select distinct breakdown_type from datathon_warehouse.mart_daily_conversion_breakdown order by 1
```

```sql _breakdown_values
select distinct breakdown_value from datathon_warehouse.mart_daily_conversion_breakdown order by 1
```

```sql funnel_summary
select
    breakdown_value as dimension,
    sum(order_count) as total_orders,
    sum(revenue) as total_revenue,
    avg(approx_conversion_rate) as avg_conversion_rate,
    cast(sum(cancelled_lines) as double) / nullif(sum(order_line_count), 0) as avg_cancellation_rate,
    cast(sum(revenue) as double) / nullif(sum(order_count), 0) as avg_aov
from datathon_warehouse.mart_daily_conversion_breakdown
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
  and breakdown_type in ${inputs.type_filter.value}
  and breakdown_value in ${inputs.value_filter.value}
group by 1
order by avg_conversion_rate desc
```

```sql conversion_trend
select
    sales_date,
    breakdown_type,
    breakdown_value,
    approx_conversion_rate,
    cancellation_rate,
    order_count,
    revenue
from datathon_warehouse.mart_daily_conversion_breakdown
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
  and breakdown_type in ${inputs.type_filter.value}
  and breakdown_value in ${inputs.value_filter.value}
order by sales_date
```

```sql device_conversion
select
    breakdown_value as device_type,
    avg(approx_conversion_rate) as avg_conversion_rate,
    cast(sum(cancelled_lines) as double) / nullif(sum(order_line_count), 0) as avg_cancellation_rate,
    cast(sum(revenue) as double) / nullif(sum(order_count), 0) as avg_aov,
    sum(order_count) as total_orders
from datathon_warehouse.mart_daily_conversion_breakdown
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
  and breakdown_type = 'device_type'
group by 1
order by avg_conversion_rate desc
```

```sql tablet_conversion
select avg_conversion_rate
from ${device_conversion}
where device_type = 'tablet'
```

```sql payment_conversion
select
    breakdown_value as payment_method,
    avg(approx_conversion_rate) as avg_conversion_rate,
    cast(sum(cancelled_lines) as double) / nullif(sum(order_line_count), 0) as avg_cancellation_rate,
    cast(sum(revenue) as double) / nullif(sum(order_count), 0) as avg_aov,
    sum(order_count) as total_orders
from datathon_warehouse.mart_daily_conversion_breakdown
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
  and breakdown_type = 'payment_method'
group by 1
order by avg_conversion_rate desc
```

```sql source_conversion
select
    breakdown_value as order_source,
    avg(approx_conversion_rate) as avg_conversion_rate,
    cast(sum(cancelled_lines) as double) / nullif(sum(order_line_count), 0) as avg_cancellation_rate,
    cast(sum(revenue) as double) / nullif(sum(order_count), 0) as avg_aov,
    sum(order_count) as total_orders
from datathon_warehouse.mart_daily_conversion_breakdown
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
  and breakdown_type = 'order_source'
group by 1
order by avg_conversion_rate desc
```

```sql daily_sessions_orders
select
    sales_date,
    sum(order_count) as orders,
    sum(revenue) as revenue
from datathon_warehouse.mart_daily_conversion_breakdown
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
  and breakdown_type in ${inputs.type_filter.value}
  and breakdown_value in ${inputs.value_filter.value}
group by 1
order by sales_date
```

```sql cancellation_by_payment
select
    breakdown_value as payment_method,
    cast(sum(cancelled_lines) as double) / nullif(sum(order_line_count), 0) as avg_cancellation_rate,
    sum(cancelled_lines) as total_cancelled_lines,
    sum(order_line_count) as total_lines
from datathon_warehouse.mart_daily_conversion_breakdown
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
  and breakdown_type = 'payment_method'
group by 1
order by avg_cancellation_rate desc
```

```sql all_conversion_rates
select 'Device' as dimension_type, device_type as dimension, avg_conversion_rate from ${device_conversion}
union all
select 'Payment', payment_method, avg_conversion_rate from ${payment_conversion}
union all
select 'Source', order_source, avg_conversion_rate from ${source_conversion}
```

```sql all_aov
select 'Device' as dimension_type, device_type as dimension, avg_aov from ${device_conversion}
union all
select 'Source', order_source, avg_aov from ${source_conversion}
```

<DateRange
    name=date_range
    data={_date_bounds}
    dates=sales_date
/>

<Dropdown
    name=type_filter
    data={_breakdown_types}
    value=breakdown_type
    multiple=true
    selectAllByDefault=true
    title="Breakdown Type"
/>

<Dropdown
    name=value_filter
    data={_breakdown_values}
    value=breakdown_value
    multiple=true
    selectAllByDefault=true
    title="Breakdown Value"
/>

## Demand Capture Overview

<Alert status="info">
Conversion rate is approximated using total daily sessions as denominator because web traffic 
is not segmented by device or source. Figures shown are the average of daily rates — 
a directional comparison across dimensions, not an exact period-level rate.
</Alert>

<BarChart
    data={funnel_summary}
    x=dimension
    y=avg_conversion_rate
    title="Approximate Conversion Rate by Dimension"
    subtitle="Which device, source, or payment method captures demand best"
    yAxisTitle="Conversion Rate"
    yFmt="pct2"
>
    <ReferenceLine y=0.005 label="0.5% Target" hideValue=true color=positive lineType=dashed/>
</BarChart>

<BarChart
    data={funnel_summary}
    x=dimension
    y=avg_cancellation_rate
    title="Cancellation Rate by Dimension"
    subtitle="High cancellation signals checkout friction or intent mismatch"
    yAxisTitle="Cancellation Rate"
    yFmt="pct2"
>
    <ReferenceLine y=0.10 label="10% Alert" hideValue=true color=warning/>
</BarChart>

## Conversion Rate by Dimension

<Alert status="info">
Conversion rate across device, payment method, and traffic source in a single view.
Grouped bars make cross-dimension comparison immediate — organic search and credit card
consistently outperform, while tablet and COD lag.
</Alert>

<BarChart
    data={all_conversion_rates}
    x=dimension
    y=avg_conversion_rate
    series=dimension_type
    title="Conversion Rate by Dimension"
    subtitle="Device, payment, and source — unified comparison"
    yAxisTitle="Conversion Rate"
    yFmt="pct2"
>
    <ReferenceLine y=0.005 label="0.5% Target" hideValue=true color=positive lineType=dashed/>
</BarChart>

## Average Order Value by Dimension

<Alert status="info">
AOV reveals spending behaviour by device and traffic source. Email and direct traffic
carry loyal high-value buyers; mobile AOV may be lower due to smaller screens or on-the-go intent.
</Alert>

<BarChart
    data={all_aov}
    x=dimension
    y=avg_aov
    series=dimension_type
    title="Average Order Value by Dimension"
    subtitle="Device and traffic source AOV in one view"
    yAxisTitle="AOV (VND)"
    yFmt="num0"
/>

## Payment Cancellation Friction

<Alert status="warning">
COD typically shows higher cancellation rates because customers change their mind
before the courier arrives. Credit card and digital wallets commit buyers at checkout — lower friction, lower cancellation.
</Alert>

<Alert status="positive">
Action: If COD cancellation is more than 2× credit card, introduce a "confirm by SMS" step for COD orders
to reduce last-mile waste and logistics cost.
</Alert>

<BarChart
    data={cancellation_by_payment}
    x=payment_method
    y=avg_cancellation_rate
    title="Cancellation Rate by Payment Method"
    subtitle="COD and bank transfer show highest checkout regret"
    yAxisTitle="Cancellation Rate"
    yFmt="pct2"
/>

## Conversion Trend Over Time

<Alert status="info">
Watch for divergence between traffic source conversion trends. 
If paid search conversion drops while spend stays flat, you are buying low-intent clicks — a classic CAC trap.
</Alert>

<LineChart
    data={conversion_trend}
    x=sales_date
    y=approx_conversion_rate
    series=breakdown_value
    title="Daily Conversion Rate Trend"
    subtitle="Track conversion stability by segment"
    yAxisTitle="Conversion Rate"
    yFmt="pct2"
>
    <ReferenceLine y=0.005 label="0.5% Target" hideValue=true color=positive lineType=dashed/>
</LineChart>

## Orders and Revenue Trend

<AreaChart
    data={daily_sessions_orders}
    x=sales_date
    y=orders
    title="Daily Order Count"
    subtitle="Order volume trend across selected segments"
    yAxisTitle="Orders"
    yFmt="0"
/>

<DataTable data={funnel_summary} rows=10 />

## Related Stories

- [Demand Capture Crisis](/stories/marketing/01-demand-capture-crisis)
- [06 Device Blind Spot](/stories/marketing/06-device-blind-spot)

