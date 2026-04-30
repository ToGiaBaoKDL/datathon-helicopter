---
title: The Shipment Blind Spot
---

<Alert status="warning">
<b>The question:</b> <Value data={shipment_gap} column=without_shipment fmt=0/> non-cancelled orders have no shipment record — including <Value data={delivered_gap} column=delivered_no_shipment fmt=0/> orders marked "delivered" in 2022. 
How does a delivered order exist without a shipment trail?
</Alert>

```sql shipment_gap
select
    sum(total_orders) as total_orders,
    sum(orders_with_shipment) as with_shipment,
    sum(orders_without_shipment) as without_shipment,
    round(sum(orders_without_shipment)::double / nullif(sum(total_orders), 0), 4) as gap_rate
from datathon_warehouse.mart_daily_shipment_coverage
where order_status not in ('cancelled')
```

```sql status_breakdown
select
    order_status,
    sum(total_orders) as total_orders,
    sum(orders_without_shipment) as no_shipment_orders,
    round(sum(orders_without_shipment)::double / nullif(sum(total_orders), 0), 4) as gap_rate
from datathon_warehouse.mart_daily_shipment_coverage
where order_status in ('delivered', 'shipped', 'returned')
group by 1
order by gap_rate desc
```

```sql delivered_gap
select
    sum(case when order_status = 'delivered' then orders_without_shipment else 0 end) as delivered_no_shipment,
    sum(case when order_status = 'delivered' then total_orders else 0 end) as delivered_total
from datathon_warehouse.mart_daily_shipment_coverage
```

```sql delivered_by_year
select
    date_part('year', sales_date)::int as year,
    sum(orders_without_shipment) as delivered_no_shipment
from datathon_warehouse.mart_daily_shipment_coverage
where order_status = 'delivered'
group by 1
order by 1
```

```sql coverage_trend
select
    date_part('year', sales_date)::int as year,
    round(avg(shipment_coverage_rate), 4) as avg_coverage
from datathon_warehouse.mart_daily_shipment_coverage
where order_status not in ('cancelled')
group by 1
order by 1
```

```sql what_if_coverage
with base as (
    select
        sum(total_orders) as total_orders,
        sum(orders_with_shipment) as with_shipment,
        sum(orders_without_shipment) as without_shipment,
        round(sum(orders_with_shipment)::double / nullif(sum(total_orders), 0), 4) as overall_coverage
    from datathon_warehouse.mart_daily_shipment_coverage
    where order_status not in ('cancelled')
)
select
    total_orders,
    with_shipment,
    without_shipment,
    overall_coverage,
    round(total_orders * 0.95, 0) as target_orders_with_shipment,
    round(target_orders_with_shipment - with_shipment, 0) as gap_to_target,
    round((0.95 - overall_coverage) * total_orders, 0) as gap_orders
from base
```

## 1. The Gap: Non-Cancelled Orders Lack Shipment Data

<Alert status="info">
Out of <Value data={shipment_gap} column=total_orders fmt=0/> non-cancelled orders, 
<Value data={shipment_gap} column=without_shipment fmt=0/> have no shipment record. 
That is <Value data={shipment_gap} column=gap_rate fmt=pct2/> of all active orders.
</Alert>

<BarChart
    data={status_breakdown}
    x=order_status
    y=gap_rate
    title="Shipment Gap Rate by Order Status"
    subtitle="Paid and created orders lack shipment by design — delivered should not"
    yAxisTitle="Gap Rate"
    yFmt="pct2"
/>

## 2. The Red Flag: Delivered Without Shipment

<Alert status="info">
<Value data={delivered_gap} column=delivered_no_shipment fmt=0/> out of <Value data={delivered_gap} column=delivered_total fmt=0/> delivered orders have no shipment record. 
These orders claim to have reached the customer but lack any logistics trail. 
This is either a data integrity failure or an operational blind spot.
</Alert>

<Grid cols=2>
    <BigValue
        data={delivered_gap}
        value=delivered_no_shipment
        title="Delivered — No Shipment"
        fmt="0"
    />
    <BigValue
        data={delivered_gap}
        value=delivered_total
        title="Total Delivered Orders"
        fmt="0"
    />
</Grid>

## 3. The Timeline: When the Blind Spot Appeared

<Alert status="info">
The delivered-without-shipment gap is not historical — it is recent. 
All <Value data={delivered_gap} column=delivered_no_shipment fmt=0/> cases occurred in a single year, suggesting a system integration failure.
</Alert>

<BarChart
    data={delivered_by_year}
    x=year
    y=delivered_no_shipment
    title="Delivered Orders Without Shipment by Year"
    subtitle="The gap is concentrated in recent history"
    yAxisTitle="Orders"
    yFmt="0"
/>

## 4. Coverage Trend: Daily Fluctuation Reveals Blind Spots

<Alert status="info">
Overall shipment coverage is <b><Value data={what_if_coverage} column=overall_coverage fmt=pct2/></b> 
(<Value data={what_if_coverage} column=with_shipment fmt=0/> of <Value data={what_if_coverage} column=total_orders fmt=0/> non-cancelled orders).
However, daily coverage fluctuates wildly — some days near 100%, others near 0%.
These troughs create operational blind spots where customer service cannot track order status.
</Alert>

<LineChart
    data={coverage_trend}
    x=year
    y=avg_coverage
    title="Average Daily Shipment Coverage Rate by Year"
    subtitle="Daily averages mask high overall coverage — trough days create blind spots"
    yAxisTitle="Coverage Rate"
    yFmt="pct2"
>
    <ReferenceLine y=0.95 label="95% Target" hideValue=true color=positive lineType=dashed/>
</LineChart>

## 5. The Real Issue: Data Integrity at the Edges

<Alert status="info">
While overall coverage is strong (<Value data={what_if_coverage} column=overall_coverage fmt=pct2/>),
<Value data={what_if_coverage} column=without_shipment fmt=0/> non-cancelled orders still lack shipment records.
Among them, <b><Value data={delivered_gap} column=delivered_no_shipment fmt=0/> delivered orders</b> have no logistics trail whatsoever.
This is not a coverage problem — it is a <b>data integrity</b> problem at the edge cases.
</Alert>

<Grid cols=3>
    <BigValue
        data={what_if_coverage}
        value=overall_coverage
        title="Overall Coverage"
        fmt="pct2"
    />
    <BigValue
        data={what_if_coverage}
        value=without_shipment
        title="Orders Without Shipment"
        fmt="0"
    />
    <BigValue
        data={delivered_gap}
        value=delivered_no_shipment
        title="Delivered — No Shipment"
        fmt="0"
    />
</Grid>

## The Verdict

<Alert status="positive">
<b>Action:</b> Audit the order-to-shipment data pipeline immediately.
The <Value data={delivered_gap} column=delivered_no_shipment fmt=0/> delivered orders without shipment records suggest an ETL or logistics integration failure at the edge.
Overall coverage at <Value data={what_if_coverage} column=overall_coverage fmt=pct2/> is healthy, 
but the <Value data={what_if_coverage} column=without_shipment fmt=0/> remaining orders — especially delivered-without-shipment — 
are a compliance and customer-service liability that demands root-cause analysis.
</Alert>

## Deep Dive

- [Fulfillment And Returns](/eda/operations/01-fulfillment-and-returns)

