---
title: Geographic Fulfillment and Regional Profile
---

This page maps commercial performance, delivery efficiency, and logistics cost across regions. 
It identifies where revenue is strong but fulfillment is weak — the classic growth bottleneck.

```sql _regions
select distinct region from datathon_warehouse.mart_region_fulfillment_profile order by 1
```

```sql region_top
select region, total_revenue
from datathon_warehouse.mart_region_fulfillment_profile
where region in ${inputs.region_filter.value}
order by total_revenue desc
limit 1
```

```sql region_highest_fee
select region, avg_shipping_fee
from datathon_warehouse.mart_region_fulfillment_profile
where region in ${inputs.region_filter.value}
order by avg_shipping_fee desc
limit 1
```

<Dropdown
    name=region_filter
    data={_regions}
    value=region
    multiple=true
    selectAllByDefault=true
    title="Region"
/>

```sql region_summary
select
    region,
    total_orders,
    total_customers,
    total_revenue,
    gross_margin_rate,
    total_units_sold,
    shipped_orders,
    avg_days_to_deliver,
    avg_shipping_fee,
    free_shipping_share,
    return_unit_rate
from datathon_warehouse.mart_region_fulfillment_profile
where region in ${inputs.region_filter.value}
order by total_revenue desc
```

```sql region_revenue
select
    region,
    total_revenue,
    gross_margin_rate,
    total_customers
from datathon_warehouse.mart_region_fulfillment_profile
where region in ${inputs.region_filter.value}
order by total_revenue desc
```

```sql region_fulfillment
select
    region,
    avg_days_to_deliver,
    avg_days_to_ship,
    avg_shipping_fee,
    free_shipping_share,
    return_unit_rate
from datathon_warehouse.mart_region_fulfillment_profile
where region in ${inputs.region_filter.value}
order by avg_days_to_deliver desc
```

```sql region_category_matrix
select
    region,
    category,
    orders,
    revenue,
    units_sold
from datathon_warehouse.mart_region_category_revenue
where region in ${inputs.region_filter.value}
order by region, revenue desc
```

```sql top_cities
select
    city,
    region,
    orders,
    customers,
    revenue
from datathon_warehouse.mart_top_cities
where region in ${inputs.region_filter.value}
order by revenue desc
```

## Regional Revenue and Margin

<Alert status="info">
Regional revenue distribution reveals market concentration. 
The East region drives the majority of revenue. Geographic diversification is a strategic priority 
to reduce single-region risk from logistics disruption, local competition, or regulatory changes.
</Alert>

<BarChart
    swapXY=true
    data={region_revenue}
    x=region
    y=total_revenue
    title="Revenue by Region"
    subtitle="Geographic revenue concentration"
    yAxisTitle="Revenue"
    yFmt="num0"
>
    <ReferencePoint data={region_top} x=region y=total_revenue label="Top region" labelPosition=top color=info/>
</BarChart>

<BarChart
    swapXY=true
    data={region_revenue}
    x=region
    y=gross_margin_rate
    title="Gross Margin Rate by Region"
    subtitle="Which regions are most profitable"
    yAxisTitle="Margin Rate"
    yFmt="pct2"
>
    <ReferenceLine y=0.15 label="15% Target" hideValue=true color=positive/>
</BarChart>

<BarChart
    swapXY=true
    data={region_revenue}
    x=region
    y=total_customers
    title="Active Customers by Region"
    subtitle="Customer base size per region"
    yAxisTitle="Customers"
    yFmt="0"
/>

## Fulfillment Efficiency by Region

<Alert status="warning">
All regions show similar delivery times, but the West has the highest shipping fee per order.
West also carries the lowest revenue share, suggesting a cost-revenue mismatch that may erode margin on cross-country shipments.
</Alert>

<Alert status="info">
<b>Uniform delivery speed is a data signal, not a coincidence.</b> The raw dataset shows delivery times
are synthetically distributed around 6 days for all regions (Central avg=6.00, East avg=6.00, West avg=6.00).
This indicates a centralized logistics network with a single SLA target rather than regionalized fulfillment.
Real-world businesses typically see East→West or urban→rural variation. If your dataset were real,
uniformity would suggest either (a) one national carrier with rigid SLA, or (b) data generation artifact.
</Alert>

<Alert status="positive">
Action: Model whether a regional hub in the West can reduce shipping costs and improve margin,
given that current delivery speed is already uniform (~6 days) across all regions.
</Alert>

<BarChart
    swapXY=true
    data={region_fulfillment}
    x=region
    y=avg_days_to_deliver
    title="Average Delivery Days by Region"
    subtitle="End-to-end fulfillment speed"
    yAxisTitle="Days"
    yFmt="0.0"
>
    <ReferenceLine y=7 label="7-Day SLA" hideValue=true color=warning/>
</BarChart>

<BarChart
    swapXY=true
    data={region_fulfillment}
    x=region
    y=avg_shipping_fee
    title="Average Shipping Fee by Region"
    subtitle="Logistics cost per order by region"
    yAxisTitle="Shipping Fee"
    yFmt="num0"
>
    <ReferencePoint data={region_highest_fee} x=region y=avg_shipping_fee label="Highest fee" labelPosition=top color=warning/>
</BarChart>

<BarChart
    swapXY=true
    data={region_fulfillment}
    x=region
    y=return_unit_rate
    title="Return Rate by Region"
    subtitle="Quality or sizing issues by geography"
    yAxisTitle="Return Rate"
    yFmt="pct2"
>
    <ReferenceLine y=0.05 label="5% Alert" hideValue=true color=warning/>
</BarChart>

## Region × Category Heatmap

<Alert status="info">
This matrix reveals regional category preferences. 
A strong diagonal (one category dominating one region) suggests localised marketing opportunity. 
A flat matrix suggests homogenous demand — site-wide campaigns work fine.
</Alert>

<Heatmap
    data={region_category_matrix}
    x=category
    y=region
    value=revenue
    title="Revenue by Region and Category"
    subtitle="Regional category preference intensity"
    valueFmt="num0"
/>

## Top Cities

<Alert status="info">
City-level detail within regions. Top cities are candidates for same-day or next-day delivery pilots,
local influencer partnerships, and offline pop-up stores.
</Alert>

<DataTable data={top_cities} rows=10>
    <Column id=city title="City"/>
    <Column id=region title="Region"/>
    <Column id=orders title="Orders" fmt=0/>
    <Column id=customers title="Customers" fmt=0/>
    <Column id=revenue title="Revenue" fmt=num0/>
</DataTable>

## Regional Profile Summary

<DataTable data={region_summary} rows=10>
    <Column id=region title="Region"/>
    <Column id=total_orders title="Orders" fmt=0/>
    <Column id=total_customers title="Customers" fmt=0/>
    <Column id=total_revenue title="Revenue" fmt=num0/>
    <Column id=gross_margin_rate title="Margin" fmt=pct2/>
    <Column id=total_units_sold title="Units" fmt=0/>
    <Column id=shipped_orders title="Shipped" fmt=0/>
    <Column id=avg_days_to_deliver title="Delivery Days" fmt=0.0/>
    <Column id=avg_shipping_fee title="Shipping Fee" fmt=num0/>
    <Column id=free_shipping_share title="Free Shipping" fmt=pct2/>
    <Column id=return_unit_rate title="Return Rate" fmt=pct2/>
</DataTable>

## Related Stories

- [Geographic Cost Puzzle](/stories/operations/01-geographic-cost-puzzle)

