---
title: Payment Mix and Checkout Friction
---

# Payment Mix and Checkout Friction

This page analyses how payment method, instalment plans, and checkout flow affect 
order completion, cancellation, and average order value.

```sql _date_bounds
select sales_date from datathon_warehouse.mart_forecast_daily_base
```

```sql _payment_methods
select distinct payment_method from datathon_warehouse.mart_daily_payment_checkout_kpis order by 1
```

<DateRange
    name=date_range
    data={_date_bounds}
    dates=sales_date
/>

<Dropdown
    name=payment_filter
    data={_payment_methods}
    value=payment_method
    multiple=true
    selectAllByDefault=true
    title="Payment Method"
/>

```sql payment_summary
select
    payment_method,
    sum(order_count) as total_orders,
    sum(revenue) as total_revenue,
    cast(sum(revenue) as double) / nullif(sum(order_count), 0) as avg_aov,
    cast(sum(cancelled_lines) as double) / nullif(sum(order_line_count), 0) as avg_cancellation_rate,
    cast(sum(installment_orders) as double) / nullif(sum(order_count), 0) as avg_installment_share,
    cast(sum(avg_payment_value * order_count) as double) / nullif(sum(order_count), 0) as avg_payment_value
from datathon_warehouse.mart_daily_payment_checkout_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
  and payment_method in ${inputs.payment_filter.value}
group by 1
order by total_revenue desc
```

```sql cod_cancellation
select avg_cancellation_rate
from ${payment_summary}
where payment_method = 'cod'
```

```sql cod_share
select
    cast(sum(case when payment_method = 'cod' then order_count else 0 end) as double)
        / nullif(sum(order_count), 0) as cod_order_share,
    cast(sum(case when payment_method = 'cod' then cancelled_lines else 0 end) as double)
        / nullif(sum(case when payment_method = 'cod' then order_line_count else 0 end), 0) as cod_cancellation_rate,
    cast(sum(case when payment_method != 'cod' then cancelled_lines else 0 end) as double)
        / nullif(sum(case when payment_method != 'cod' then order_line_count else 0 end), 0) as prepaid_cancellation_rate
from datathon_warehouse.mart_daily_payment_checkout_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
  and payment_method in ${inputs.payment_filter.value}
```

```sql payment_trend
select
    sales_date,
    payment_method,
    revenue,
    order_count,
    cancellation_rate,
    avg_order_value,
    installment_share
from datathon_warehouse.mart_daily_payment_checkout_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
  and payment_method in ${inputs.payment_filter.value}
order by sales_date
```

```sql payment_mix_over_time
select
    sales_date,
    payment_method,
    revenue
from datathon_warehouse.mart_daily_payment_checkout_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
  and payment_method in ${inputs.payment_filter.value}
order by sales_date
```

```sql installment_impact
select
    payment_method,
    cast(sum(revenue) as double) / nullif(sum(order_count), 0) as avg_aov,
    avg(avg_installments) as avg_installments,
    cast(sum(installment_orders) as double) / nullif(sum(order_count), 0) as installment_share,
    sum(installment_orders) as total_installment_orders
from datathon_warehouse.mart_daily_payment_checkout_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
  and payment_method in ${inputs.payment_filter.value}
group by 1
order by avg_aov desc
```

```sql cod_vs_prepaid
select
    case when payment_method = 'cod' then 'COD' else 'Prepaid' end as payment_group,
    sum(order_count) as total_orders,
    sum(revenue) as total_revenue,
    cast(sum(cancelled_lines) as double) / nullif(sum(order_line_count), 0) as avg_cancellation_rate,
    cast(sum(revenue) as double) / nullif(sum(order_count), 0) as avg_aov
from datathon_warehouse.mart_daily_payment_checkout_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
  and payment_method in ${inputs.payment_filter.value}
group by 1
order by total_revenue desc
```

```sql daily_cancellation
select
    sales_date,
    payment_method,
    cancellation_rate,
    cancelled_lines
from datathon_warehouse.mart_daily_payment_checkout_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
  and payment_method in ${inputs.payment_filter.value}
order by sales_date
```

## Payment Method Mix

<Alert status="info">
Credit card and COD usually dominate e-commerce payment mix in Vietnam. 
The ratio between them indicates customer trust (credit card = trust in platform) 
and purchase urgency (COD = hesitation or first-time buyer caution).
</Alert>

<Alert status="positive">
Action: COD accounts for <Value data={cod_share} column=cod_order_share fmt=pct1/> of orders but cancels at <Value data={cod_share} column=cod_cancellation_rate fmt=pct1/> — roughly double the prepaid rate (<Value data={cod_share} column=prepaid_cancellation_rate fmt=pct1/>). 
Launch a "first-order discount for credit card" campaign to shift the mix toward lower-friction payment methods.
</Alert>

<BarChart
    data={payment_summary}
    x=payment_method
    y=total_revenue
    title="Revenue by Payment Method"
    subtitle="Which payment instruments drive the most revenue"
    yAxisTitle="Revenue"
    yFmt="num0"
/>

<AreaChart
    data={payment_mix_over_time}
    x=sales_date
    y=revenue
    series=payment_method
    title="Payment Mix Trend Over Time"
    subtitle="Revenue share shift between payment methods"
    yAxisTitle="Revenue"
    yFmt="num0"
/>

## Checkout Friction: Cancellation by Payment

<Alert status="warning">
COD cancellation is the silent profit killer: <Value data={cod_share} column=cod_cancellation_rate fmt=pct1/> of COD orders are cancelled vs <Value data={cod_share} column=prepaid_cancellation_rate fmt=pct1/> for prepaid. 
Every cancelled COD order incurs packing, logistics routing, and return costs with zero revenue.
</Alert>

<BarChart
    data={payment_summary}
    x=payment_method
    y=avg_cancellation_rate
    title="Cancellation Rate by Payment Method"
    subtitle="COD and bank transfer show highest buyer remorse"
    yAxisTitle="Cancellation Rate"
    yFmt="0.0%"
>
    <ReferencePoint data={cod_cancellation} x="cod" y=avg_cancellation_rate label="2x prepaid" labelPosition=top color=negative/>
</BarChart>

<LineChart
    data={daily_cancellation}
    x=sales_date
    y=cancellation_rate
    series=payment_method
    title="Daily Cancellation Rate by Payment"
    subtitle="Track payment-level checkout stability"
    yAxisTitle="Cancellation Rate"
    yFmt="0.0%"
/>

## Instalment Impact on AOV

<Alert status="info">
Installment penetration is high for non-COD methods, 
but COD has 0% installment penetration by design. Interestingly, AOV is nearly identical 
across all payment methods, suggesting that installment availability does not 
drive spend level — it simply removes friction for purchases shoppers already intend to make.
</Alert>

<BarChart
    data={installment_impact}
    x=payment_method
    y=avg_aov
    title="Average Order Value by Payment Method"
    subtitle="Instalment-friendly methods attract higher spend"
    yAxisTitle="AOV"
    yFmt="num0"
/>

<BarChart
    data={installment_impact}
    x=payment_method
    y=installment_share
    title="Instalment Share by Payment Method"
    subtitle="Which payment types support split payments"
    yAxisTitle="Share of Orders"
    yFmt="0.0%"
/>

## COD vs Prepaid Comparison

<Alert status="info">
The COD/Prepaid split is a health indicator for the business. 
High COD means high logistics cost, high return risk, and cash-flow drag 
(cash is collected on delivery, not at checkout). Prepaid shifts risk to the buyer.
</Alert>

<BarChart
    data={cod_vs_prepaid}
    x=payment_group
    y=total_revenue
    title="Revenue: COD vs Prepaid"
    subtitle="Prepaid revenue includes credit card, PayPal, Apple Pay, bank transfer"
    yAxisTitle="Revenue"
    yFmt="num0"
/>

<BarChart
    data={cod_vs_prepaid}
    x=payment_group
    y=avg_cancellation_rate
    title="Cancellation: COD vs Prepaid"
    subtitle="COD orders cancel at significantly higher rates"
    yAxisTitle="Cancellation Rate"
    yFmt="0.0%"
/>

## Payment Method Detail

<DataTable data={payment_summary} rows=10 />
