---
title: The Shipment Blind Spot
---

# The Shipment Blind Spot

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
from datathon_warehouse.mart_daily_shipment_gap
where order_status not in ('cancelled')
```

```sql status_breakdown
select
    order_status,
    sum(total_orders) as total_orders,
    sum(orders_without_shipment) as no_shipment_orders,
    round(sum(orders_without_shipment)::double / nullif(sum(total_orders), 0), 4) as gap_rate
from datathon_warehouse.mart_daily_shipment_gap
group by 1
order by gap_rate desc
```

```sql delivered_gap
select
    sum(case when order_status = 'delivered' then orders_without_shipment else 0 end) as delivered_no_shipment,
    sum(case when order_status = 'delivered' then total_orders else 0 end) as delivered_total
from datathon_warehouse.mart_daily_shipment_gap
```

```sql delivered_by_year
select
    date_part('year', sales_date)::int as year,
    sum(orders_without_shipment) as delivered_no_shipment
from datathon_warehouse.mart_daily_shipment_gap
where order_status = 'delivered'
group by 1
order by 1
```

```sql coverage_trend
select
    date_part('year', sales_date)::int as year,
    round(avg(shipment_coverage_rate), 4) as avg_coverage
from datathon_warehouse.mart_daily_shipment_gap
where order_status not in ('cancelled')
group by 1
order by 1
```

## 1. The Gap: 3.6% of Non-Cancelled Orders Lack Shipment Data

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

## 4. Coverage Trend: Are We Losing Visibility?

<Alert status="info">
Shipment coverage rate for non-cancelled orders has hovered around 62–66% for a decade. 
This low baseline suggests a structural integration gap between order and logistics systems.
</Alert>

<LineChart
    data={coverage_trend}
    x=year
    y=avg_coverage
    title="Shipment Coverage Rate by Year"
    subtitle="Coverage has plateaued below two-thirds for a decade"
    yAxisTitle="Coverage Rate"
    yFmt="pct2"
>
    <ReferenceLine y=0.95 label="95% Target" hideValue=true color=positive lineType=dashed/>
</LineChart>

## The Verdict

<Alert status="positive">
<b>Action:</b> Audit the order-to-shipment data pipeline immediately. 
The <Value data={delivered_gap} column=delivered_no_shipment fmt=0/> delivered orders without shipment records in 2022 suggest an ETL or logistics integration failure. 
All non-cancelled orders should have shipment coverage above 95%. 
Current coverage at ~63% means one in three orders is invisible to operations — a compliance and customer-service liability.
</Alert>
