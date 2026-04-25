---
title: Conversion Funnel and Traffic Quality
---

# Conversion Funnel and Traffic Quality

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
    yFmt="0.0%"
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
    yFmt="0.0%"
>
    <ReferenceLine y=0.10 label="10% Alert" hideValue=true color=warning/>
</BarChart>

## Device Performance

<Alert status="info">
Mobile conversion edges out desktop, suggesting strong mobile UX or a desktop segment 
that skews toward browsing without buying. Tablet conversion is notably lower — investigate whether 
tablet UX has friction or whether tablet users are earlier in the purchase journey.
</Alert>

<BarChart
    data={device_conversion}
    x=device_type
    y=avg_conversion_rate
    title="Conversion Rate by Device Type"
    subtitle="Desktop vs mobile vs tablet demand capture"
    yAxisTitle="Conversion Rate"
    yFmt="0.0%"
>
    <ReferenceLine y=0.005 label="0.5% Target" hideValue=true color=positive lineType=dashed/>
    <ReferencePoint data={tablet_conversion} x="tablet" y=avg_conversion_rate label="Investigate UX" labelPosition=top color=warning/>
</BarChart>

<BarChart
    data={device_conversion}
    x=device_type
    y=avg_aov
    title="Average Order Value by Device"
    subtitle="Do desktop shoppers spend more per order"
    yAxisTitle="AOV"
    yFmt="num0"
/>

## Payment Method Friction

<Alert status="warning">
COD typically shows higher cancellation rates because customers change their mind 
before the courier arrives. Credit card and digital wallets commit buyers at checkout — lower friction, lower cancellation.
</Alert>

<Alert status="positive">
Action: If COD cancellation is >2× credit card, introduce a "confirm by SMS" step for COD orders 
to reduce last-mile waste and logistics cost.
</Alert>

<BarChart
    data={payment_conversion}
    x=payment_method
    y=avg_conversion_rate
    title="Conversion Rate by Payment Method"
    subtitle="Credit card and digital wallets convert best"
    yAxisTitle="Conversion Rate"
    yFmt="0.0%"
/>

<BarChart
    data={cancellation_by_payment}
    x=payment_method
    y=avg_cancellation_rate
    title="Cancellation Rate by Payment Method"
    subtitle="COD and bank transfer show highest checkout regret"
    yAxisTitle="Cancellation Rate"
    yFmt="0.0%"
/>

## Traffic Source Quality

<Alert status="info">
Organic search typically shows strong conversion because buyer intent is high. 
Paid search and social may drive volume but can attract lower-intent traffic. 
Email and direct traffic often carry loyal, higher-value buyers.
</Alert>

<BarChart
    data={source_conversion}
    x=order_source
    y=avg_conversion_rate
    title="Conversion Rate by Traffic Source"
    subtitle="Organic search vs paid vs social vs email"
    yAxisTitle="Conversion Rate"
    yFmt="0.0%"
/>

<BarChart
    data={source_conversion}
    x=order_source
    y=avg_aov
    title="Average Order Value by Traffic Source"
    subtitle="Email and direct traffic often carry loyal high-value buyers"
    yAxisTitle="AOV"
    yFmt="num0"
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
    yFmt="0.0%"
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
