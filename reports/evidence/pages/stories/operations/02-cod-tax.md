---
title: The COD Tax
---

<Alert status="warning">
<b>The question:</b> COD (Cash on Delivery) accounts for a large order share but cancels at roughly <b><Value data={cod_cancel_ratio} column=ratio fmt=0.0/>×</b> the prepaid rate. 
What is the real cost of COD preference?
</Alert>

```sql payment_summary
select
    payment_method,
    sum(order_count) as total_orders,
    sum(revenue) as total_revenue,
    round(sum(cancelled_lines)::double / nullif(sum(order_line_count), 0), 4) as avg_cancellation_rate,
    round(sum(revenue)::double / sum(order_count), 0) as avg_order_value
from datathon_warehouse.mart_daily_payment_checkout_kpis
where payment_method != 'unknown'
group by 1
order by total_orders desc
```

```sql cod_vs_prepaid
select
    case
        when payment_method = 'cod' then 'COD'
        else 'Prepaid'
    end as payment_group,
    sum(order_count) as total_orders,
    sum(revenue) as total_revenue,
    round(sum(cancelled_lines)::double / nullif(sum(order_line_count), 0), 4) as avg_cancellation_rate,
    round(sum(revenue)::double / sum(order_count), 0) as avg_order_value
from datathon_warehouse.mart_daily_payment_checkout_kpis
where payment_method != 'unknown'
group by 1
order by total_orders desc
```

```sql cod_rate
select round(sum(cancelled_lines)::double / nullif(sum(order_line_count), 0), 4) as cod_cancel_rate
from datathon_warehouse.mart_daily_payment_checkout_kpis
where payment_method = 'cod'
```

```sql prepaid_rate
select round(sum(cancelled_lines)::double / nullif(sum(order_line_count), 0), 4) as prepaid_cancel_rate
from datathon_warehouse.mart_daily_payment_checkout_kpis
where payment_method != 'cod' and payment_method != 'unknown'
```

```sql cod_share
select
    round(sum(case when payment_method = 'cod' then order_count else 0 end)::double / sum(order_count), 4) as cod_order_pct
from datathon_warehouse.mart_daily_payment_checkout_kpis
where payment_method != 'unknown'
```

```sql what_if_shift
select
    round(sum(case when payment_method = 'cod' then order_count else 0 end) * 0.10, 0) as shifted_orders,
    round(sum(case when payment_method = 'cod' then order_count else 0 end) * 0.10 * ((select cod_cancel_rate from ${cod_rate}) - (select prepaid_cancel_rate from ${prepaid_rate})), 0) as saved_orders
from datathon_warehouse.mart_daily_payment_checkout_kpis
where payment_method != 'unknown'
```

```sql cod_cancel_ratio
select
    round(
        (select sum(cancelled_lines)::double / nullif(sum(order_line_count), 0) from datathon_warehouse.mart_daily_payment_checkout_kpis where payment_method = 'cod')
        / nullif((select sum(cancelled_lines)::double / nullif(sum(order_line_count), 0) from datathon_warehouse.mart_daily_payment_checkout_kpis where payment_method != 'cod' and payment_method != 'unknown'), 0),
        1
    ) as ratio
```

```sql daily_payment_trend
select
    sales_date,
    case when payment_method = 'cod' then 'COD' else 'Prepaid' end as payment_group,
    round(sum(cancelled_lines)::double / nullif(sum(order_line_count), 0), 4) as cancellation_rate
from datathon_warehouse.mart_daily_payment_checkout_kpis
where payment_method != 'unknown'
group by 1, 2
order by sales_date
```

## 1. The Split: COD Dominates Order Volume

<Alert status="info">
COD represents a large share of orders. But the cancellation rate is <b><Value data={cod_rate} column=cod_cancel_rate fmt=pct2/></b> vs <b><Value data={prepaid_rate} column=prepaid_cancel_rate fmt=pct2/></b> for prepaid — a <b><Value data={cod_cancel_ratio} column=ratio fmt=0.0/>×</b> gap. 
Every cancelled COD order incurs packing, routing, and return costs with zero revenue.
</Alert>

<BarChart
    data={payment_summary}
    x=payment_method
    y=total_orders
    title="Total Orders by Payment Method"
    subtitle="COD accounts for the largest order share"
    yAxisTitle="Orders"
    yFmt="0"
/>

<BarChart
    data={payment_summary}
    x=payment_method
    y=avg_cancellation_rate
    title="Cancellation Rate by Payment Method"
    subtitle="COD cancellation rate vs all prepaid methods"
    yAxisTitle="Cancellation Rate"
    yFmt="pct2"
/>

## 2. The Gap: COD vs Prepaid Aggregated

<Alert status="info">
Aggregated into COD vs Prepaid, the pattern is stark. 
AOV is nearly identical — the friction is psychological (trust), not economic (ability to pay).
</Alert>

<BarChart
    data={cod_vs_prepaid}
    x=payment_group
    y=avg_cancellation_rate
    title="Cancellation Rate: COD vs Prepaid"
    subtitle="Same AOV, different trust levels"
    yAxisTitle="Cancellation Rate"
    yFmt="pct2"
/>

<BarChart
    data={cod_vs_prepaid}
    x=payment_group
    y=avg_order_value
    title="Average Order Value: COD vs Prepaid"
    subtitle="AOV parity — the issue is trust, not purchasing power"
    yAxisTitle="AOV (VND)"
    yFmt="num0"
/>

## 3. Daily Trend: Persistent, Not Spiking

<Alert status="info">
The COD cancellation premium is persistent across time. It is not a seasonal spike — it is a structural tax on the business model.
</Alert>

<LineChart
    data={daily_payment_trend}
    x=sales_date
    y=cancellation_rate
    series=payment_group
    title="Daily Cancellation Rate by Payment Group"
    subtitle="COD cancellation premium is structural and persistent"
    yAxisTitle="Cancellation Rate"
    yFmt="pct2"
/>

## 4. What-If: Shift 10% COD → Prepaid

<Alert status="info">
If <b>10%</b> of COD orders shifted to prepaid, <b><Value data={what_if_shift} column=saved_orders fmt=0/></b> orders would be saved from cancellation. 
At current AOV, that is substantial recovered revenue with zero marketing spend. 
Caveat: shifted COD users may not instantly match prepaid cancellation rates due to self-selection bias (higher-trust customers already choose prepaid).
</Alert>

<Grid cols=2>
    <BigValue
        data={what_if_shift}
        value=shifted_orders
        title="Orders Shifted (10%)"
        fmt="0"
    />
    <BigValue
        data={what_if_shift}
        value=saved_orders
        title="Orders Saved from Cancel"
        fmt="0"
    />
</Grid>

## The Verdict

<Alert status="positive">
<b>Action:</b> COD cancellation is <b><Value data={cod_cancel_ratio} column=ratio fmt=0.0/>×</b> prepaid — a structural tax. 
Launch a "first-order credit card discount" campaign to build prepaid habit. 
Deploy SMS confirmation for COD orders to reduce impulse cancellations. 
A 10% COD-to-prepaid shift would save <Value data={what_if_shift} column=saved_orders fmt=0/> orders with zero ad spend.
</Alert>

## Deep Dive

- [Payment And Checkout](/eda/finance/02-payment-and-checkout)

