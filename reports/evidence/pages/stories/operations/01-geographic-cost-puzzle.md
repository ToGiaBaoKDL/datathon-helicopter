---
title: The Geographic Cost Puzzle
---

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

```sql region_category_share
select
    region,
    category,
    round(revenue::double / sum(revenue) over (partition by region), 4) as share
from datathon_warehouse.mart_region_category_revenue
order by region, share desc
```

```sql region_aov
select
    region,
    round(total_revenue::double / total_orders, 0) as aov
from datathon_warehouse.mart_region_fulfillment_profile
order by aov desc
```

```sql category_return_rate
select
    category,
    round(sum(return_units)::double / nullif(sum(total_units_sold), 0), 4) as weighted_return_rate
from datathon_warehouse.mart_product_lifetime_performance
where lifecycle_stage != 'never_sold'
group by 1
order by weighted_return_rate desc
```

```sql top_return_categories
select
    category,
    round(sum(return_units)::double / nullif(sum(total_units_sold), 0), 4) as weighted_return_rate,
    count(*) as sku_count,
    round(sum(total_revenue), 0) as total_revenue
from datathon_warehouse.mart_product_lifetime_performance
where lifecycle_stage != 'never_sold'
group by 1
order by weighted_return_rate desc
```

```sql region_return_rank
select
    region,
    round(return_unit_rate, 4) as return_unit_rate,
    round(total_revenue, 0) as total_revenue
from datathon_warehouse.mart_region_fulfillment_profile
order by return_unit_rate desc
```

```sql what_if_west
with west as (
    select region, total_orders, total_revenue, total_units_sold, return_unit_rate, return_units, refund_amount
    from datathon_warehouse.mart_region_fulfillment_profile
    where region = 'West'
),
east as (
    select return_unit_rate
    from datathon_warehouse.mart_region_fulfillment_profile
    where region = 'East'
)
select
    w.total_orders,
    w.total_revenue,
    w.return_units as west_return_units,
    w.return_unit_rate as west_rate,
    e.return_unit_rate as east_rate,
    round(w.total_units_sold * (w.return_unit_rate - e.return_unit_rate), 0) as avoidable_return_units,
    round(w.refund_amount * (w.return_unit_rate - e.return_unit_rate) / nullif(w.return_unit_rate, 0), 0) as avoidable_refund,
    round(avoidable_refund::double / nullif(w.total_revenue, 0), 4) as pct_of_revenue
from west w, east e
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
    subtitle="Shipping cost is uniform across all regions"
    yAxisTitle="Shipping Fee (VND)"
    yFmt="0.00"
/>

<BarChart
    data={region_profile}
    x=region
    y=avg_days_to_deliver
    title="Average Days to Deliver by Region"
    subtitle="Delivery speed is consistent across all regions"
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
The charts below reveal whether West skews toward high-return categories or has a different purchasing pattern.
If West over-indexes on a category with historically high returns, that explains the puzzle.
</Alert>

<BarChart
    data={region_category_share}
    x=category
    y=share
    series=region
    title="Category Share by Region"
    subtitle="Does West over-index on any high-return category?"
    yAxisTitle="Share of Region Revenue"
    yFmt="pct2"
/>

<BarChart
    data={region_aov}
    x=region
    y=aov
    title="Average Order Value by Region"
    subtitle="Lower AOV can indicate trial buying behavior"
    yAxisTitle="AOV (VND)"
    yFmt="num0"
/>

<Alert status="info">
The table below ranks categories by return rate. If West over-indexes on categories near the top,
the geographic puzzle is solved — it is a product-mix issue, not a regional logistics issue.
</Alert>

<DataTable data={top_return_categories} rows=10>
    <Column id=category title="Category"/>
    <Column id=weighted_return_rate title="Return Rate" fmt=pct2/>
    <Column id=sku_count title="SKUs" fmt=0/>
    <Column id=total_revenue title="Revenue" fmt=num0/>
</DataTable>

## 5. What-If: West Returns at East Level

<Alert status="info">
If West achieved the same return unit rate as East,
<Value data={what_if_west} column=avoidable_return_units fmt=0/> return units would be prevented,
saving <Value data={what_if_west} column=avoidable_refund fmt=num0/> VND in refunds.
That equals <Value data={what_if_west} column=pct_of_revenue fmt=pct2/> of West revenue — a meaningful profitability recovery for the smallest region.
</Alert>

<Grid cols=3>
    <BigValue
        data={what_if_west}
        value=west_return_units
        title="West Return Units"
        fmt="0"
    />
    <BigValue
        data={what_if_west}
        value=avoidable_return_units
        title="Avoidable Returns"
        fmt="0"
    />
    <BigValue
        data={what_if_west}
        value=avoidable_refund
        title="Refund Savings (VND)"
        fmt="num0"
    />
</Grid>

## The Verdict

<Alert status="positive">
<b>Action:</b> West has the lowest revenue share but the highest return rate (<Value data={west_return} column=return_unit_rate fmt=pct2/>).
Delivery speed and shipping fee are uniform — the issue is not logistics cost.
Investigate whether product mix in West skews toward high-return categories.
Improve sizing guides for West-targeted campaigns.
See also <a href="/stories/product/03-quality-before-growth">Story 06: Quality Before Growth</a> for return root-cause analysis.
</Alert>

## Deep Dive

- [Geographic Fulfillment](/eda/operations/02-geographic-fulfillment)

