---
title: The Geographic Cost Puzzle
---

# The Geographic Cost Puzzle

<Alert status="warning">
<b>The question:</b> East drives the most revenue. West has the highest return rate. 
Is there a cost-revenue mismatch across regions?
</Alert>

```sql region_profile
select
    region,
    round(total_revenue, 0) as total_revenue,
    round(gross_margin_rate, 4) as gross_margin_rate,
    round(return_unit_rate, 4) as return_unit_rate,
    round(avg_days_to_deliver, 1) as avg_days_to_deliver,
    round(avg_shipping_fee, 2) as avg_shipping_fee,
    total_orders
from datathon_warehouse.mart_region_fulfillment_profile
order by total_revenue desc
```

```sql top_region
select region, total_revenue
from datathon_warehouse.mart_region_fulfillment_profile
order by total_revenue desc
limit 1
```

```sql west_return
select return_unit_rate
from datathon_warehouse.mart_region_fulfillment_profile
where region = 'West'
```

```sql region_category_matrix
select
    region,
    category,
    round(revenue, 0) as revenue
from datathon_warehouse.mart_region_category_revenue
order by region, revenue desc
```

```sql region_return_rank
select
    region,
    round(return_unit_rate, 4) as return_unit_rate,
    round(total_revenue, 0) as total_revenue
from datathon_warehouse.mart_region_fulfillment_profile
order by return_unit_rate desc
```

## 1. Revenue Map: East Dominates

<Alert status="info">
<Value data={top_region} column=region/> leads with <Value data={top_region} column=total_revenue fmt=num0/> VND in revenue. 
West is the smallest region by revenue but has the highest return rate. 
The puzzle: why does the smallest region return the most?
</Alert>

<BarChart
    data={region_profile}
    x=region
    y=total_revenue
    title="Total Revenue by Region"
    subtitle="East is the revenue engine; West is the smallest"
    yAxisTitle="Revenue (VND)"
    yFmt="num0"
/>

## 2. Fulfillment Cost: Uniform Across Regions

<Alert status="info">
Shipping fee and delivery speed are nearly identical across all regions. 
This rules out logistics cost as the cause of West's underperformance. The issue is quality or product-market fit, not delivery economics.
</Alert>

<BarChart
    data={region_profile}
    x=region
    y=avg_shipping_fee
    title="Average Shipping Fee by Region"
    subtitle="Uniform ~5 VND — no regional cost advantage"
    yAxisTitle="Shipping Fee (VND)"
    yFmt="0.00"
/>

<BarChart
    data={region_profile}
    x=region
    y=avg_days_to_deliver
    title="Average Days to Deliver by Region"
    subtitle="All regions near ~6 days — uniform SLA"
    yAxisTitle="Days"
    yFmt="0.0"
>
    <ReferenceLine y=7 label="7-Day SLA" hideValue=true color=negative lineType=dashed/>
</BarChart>

## 3. Return Rate: West Is the Outlier

<Alert status="info">
West has the highest return unit rate at <b><Value data={west_return} column=return_unit_rate fmt=pct2/></b>. 
East and Central are lower. Since logistics are uniform, the cause is likely product mix or sizing mismatch in West.
</Alert>

<BarChart
    data={region_return_rank}
    x=region
    y=return_unit_rate
    title="Return Unit Rate by Region"
    subtitle="West has the highest returns despite lowest revenue"
    yAxisTitle="Return Unit Rate"
    yFmt="pct2"
>
    <ReferenceLine y=0.05 label="5% Alert" hideValue=true color=negative lineType=dashed/>
</BarChart>

## 4. Category Mix: What Each Region Buys

<Alert status="info">
The heatmap below reveals whether West skews toward high-return categories. 
If West over-indexes on a category with historically high returns, that explains the puzzle.
</Alert>

<Heatmap
    data={region_category_matrix}
    x=category
    y=region
    value=revenue
    title="Revenue Mix: Region × Category"
    subtitle="Darker = higher revenue. Reveals category preference by region"
    valueFmt="num0"
/>

## The Verdict

<Alert status="positive">
<b>Action:</b> West has the lowest revenue share but the highest return rate (<Value data={west_return} column=return_unit_rate fmt=pct2/>). 
Delivery speed and shipping fee are uniform — the issue is not logistics cost. 
Investigate whether product mix in West skews toward high-return categories. 
Improve sizing guides for West-targeted campaigns.
</Alert>
