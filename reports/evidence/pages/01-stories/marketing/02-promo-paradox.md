---
title: The Promo Paradox
---

<Alert status="warning">
<b>The question:</b> Why does the business run <Value data={pct_stats} column=campaigns fmt=0/> percentage-discount campaigns vs only <Value data={fixed_stats} column=campaigns fmt=0/> fixed-discount,
when fixed discounts deliver <b><Value data={roi_ratio} column=ratio fmt=0.0/>× higher ROI</b> per discount VND spent?
</Alert>

```sql promo_summary
select
    promo_type,
    count(*) as campaigns,
    round(sum(total_net_revenue), 0) as total_revenue,
    round(avg(discount_rate), 4) as avg_discount_rate,
    round(sum(total_net_revenue) / nullif(sum(total_discount_amount), 0), 1) as roi,
    sum(total_orders) as total_orders
from datathon_warehouse.mart_promotion_effectiveness
where total_orders > 0
group by 1
order by total_revenue desc
```

```sql fixed_stats
select
    count(*) as campaigns,
    round(sum(total_net_revenue), 0) as total_revenue,
    round(avg(discount_rate), 4) as avg_discount_rate,
    round(sum(total_net_revenue) / nullif(sum(total_discount_amount), 0), 1) as roi
from datathon_warehouse.mart_promotion_effectiveness
where total_orders > 0 and promo_type = 'fixed'
```

```sql pct_stats
select
    count(*) as campaigns,
    round(sum(total_net_revenue), 0) as total_revenue,
    round(avg(discount_rate), 4) as avg_discount_rate,
    round(sum(total_net_revenue) / nullif(sum(total_discount_amount), 0), 1) as roi
from datathon_warehouse.mart_promotion_effectiveness
where total_orders > 0 and promo_type = 'percentage'
```

```sql promo_efficiency
select
    promo_name,
    promo_type,
    discount_rate,
    total_net_revenue as total_revenue,
    total_orders
from datathon_warehouse.mart_promotion_effectiveness
where total_orders > 0
order by total_revenue desc
```

```sql category_scope
select
    coalesce(applicable_category, 'All Categories') as category_scope,
    promo_type,
    count(*) as campaigns,
    sum(total_net_revenue) as total_revenue,
    avg(discount_rate) as avg_discount_rate,
    sum(total_net_revenue) / nullif(sum(total_discount_amount), 0) as roi
from datathon_warehouse.mart_promotion_effectiveness
where total_orders > 0
group by 1, 2
order by total_revenue desc
```

```sql roi_ratio
select
    round(
        (select sum(total_net_revenue) / nullif(sum(total_discount_amount), 0) from datathon_warehouse.mart_promotion_effectiveness where total_orders > 0 and promo_type = 'fixed')
        /
        nullif((select sum(total_net_revenue) / nullif(sum(total_discount_amount), 0) from datathon_warehouse.mart_promotion_effectiveness where total_orders > 0 and promo_type = 'percentage'), 0),
        1
    ) as ratio
```

```sql channel_performance
select
    promo_channel,
    promo_type,
    count(*) as campaigns,
    sum(total_net_revenue) as total_revenue,
    avg(discount_rate) as avg_discount_rate
from datathon_warehouse.mart_promotion_effectiveness
where total_orders > 0
group by 1, 2
order by total_revenue desc
```

```sql top_campaigns
select
    promo_name,
    promo_type,
    round(total_net_revenue, 0) as total_revenue,
    total_orders,
    round(discount_rate, 4) as discount_rate,
    round(total_net_revenue / nullif(total_discount_amount, 0), 1) as roi
from datathon_warehouse.mart_promotion_effectiveness
where total_orders > 0
order by total_net_revenue desc
limit 10
```

```sql promo_scatter_roi
select
    promo_name,
    promo_type,
    round(total_net_revenue, 0) as total_revenue,
    total_orders,
    round(discount_rate, 4) as discount_rate,
    round(total_net_revenue / nullif(total_discount_amount, 0), 1) as roi
from datathon_warehouse.mart_promotion_effectiveness
where total_orders > 0
order by total_net_revenue desc
limit 50
```

```sql what_if_shift
with base as (
    select
        promo_type,
        sum(total_discount_amount) as total_discount,
        round(sum(total_net_revenue) / nullif(sum(total_discount_amount), 0), 1) as roi
    from datathon_warehouse.mart_promotion_effectiveness
    where total_orders > 0
    group by 1
),
pct as (
    select total_discount, roi from base where promo_type = 'percentage'
),
fxd as (
    select roi from base where promo_type = 'fixed'
)
select
    round(pct.total_discount * 0.10, 0) as shifted_discount,
    round(pct.total_discount * 0.10 * pct.roi, 0) as current_return,
    round(pct.total_discount * 0.10 * fxd.roi, 0) as new_return,
    round(pct.total_discount * 0.10 * (fxd.roi - pct.roi), 0) as incremental_revenue,
    round((fxd.roi - pct.roi)::double / nullif(pct.roi, 0), 4) as pct_lift
from pct, fxd
```

```sql category_aov
select
    coalesce(applicable_category, 'All Categories') as category_scope,
    promo_type,
    cast(sum(total_net_revenue) as double) / nullif(sum(total_orders), 0) as avg_aov
from datathon_warehouse.mart_promotion_effectiveness
where total_orders > 0
group by 1, 2
order by category_scope, promo_type
```

## 1. The Trade-off: Scale vs Efficiency

<Alert status="info">
Percentage: <Value data={pct_stats} column=campaigns fmt=0/> campaigns, <Value data={pct_stats} column=total_revenue fmt=num0/> VND revenue,
<Value data={pct_stats} column=avg_discount_rate fmt=pct2/> discount, <Value data={pct_stats} column=roi fmt=0.0/>× ROI.
Fixed: <Value data={fixed_stats} column=campaigns fmt=0/> campaigns, <Value data={fixed_stats} column=total_revenue fmt=num0/> VND revenue,
<Value data={fixed_stats} column=avg_discount_rate fmt=pct2/> discount, <Value data={fixed_stats} column=roi fmt=0.0/>× ROI. 
The business chooses scale over efficiency.
</Alert>

<BarChart
    data={promo_summary}
    x=promo_type
    y=total_revenue
    title="Revenue by Promotion Type"
    subtitle="Percentage drives far more absolute revenue than fixed"
    yAxisTitle="Revenue (VND)"
    yFmt="num0"
/>

<BarChart
    data={promo_summary}
    x=promo_type
    y=avg_discount_rate
    title="Average Discount Rate by Type"
    subtitle="Fixed discounts run far shallower than percentage"
    yAxisTitle="Discount Rate"
    yFmt="pct2"
/>

## 2. The Efficiency Map

<Alert status="info">
The bubble chart below maps every campaign by discount depth (x) and revenue (y), with bubble size representing order volume.
Top-left = shallow discount + high revenue = efficient winners. Bottom-right = deep discount + low revenue = margin destroyers.
</Alert>

<BubbleChart
    data={promo_efficiency}
    x=discount_rate
    y=total_revenue
    series=promo_type
    size=total_orders
    title="Campaign Efficiency: Discount Depth vs Revenue"
    subtitle="Bubble size = order volume. Top-left = efficient; bottom-right = margin destroyers"
    xAxisTitle="Discount Rate"
    yAxisTitle="Net Revenue"
    xFmt="pct2"
    yFmt="num0"
>
    <ReferenceLine x=0.15 label="15% Threshold" hideValue=true color=warning lineType=dashed/>
</BubbleChart>

<Alert status="info">
The table below ranks the top 10 campaigns by net revenue. 
High-revenue campaigns are not necessarily the most efficient — compare discount_rate and roi to find the true winners.
</Alert>

<DataTable data={top_campaigns} rows=10>
    <Column id=promo_name title="Campaign"/>
    <Column id=promo_type title="Type"/>
    <Column id=total_revenue title="Revenue" fmt=num0/>
    <Column id=total_orders title="Orders" fmt=0/>
    <Column id=discount_rate title="Discount" fmt=pct2/>
    <Column id=roi title="ROI" fmt=0.0/>
</DataTable>

## 3. Category Impact: Fixed Wins Everywhere

<Alert status="info">
Fixed discounts outperform percentage discounts across <b>all</b> category scopes. 
The efficiency gap is not limited to a single product category — it is a structural feature of the promo design.
</Alert>

<BarChart
    data={category_scope}
    x=category_scope
    y=roi
    series=promo_type
    title="ROI by Category Scope and Promo Type"
    subtitle="Fixed discounts outperform percentage across all scopes"
    yAxisTitle="ROI (Revenue per Discount VND)"
    yFmt="0.0"
/>

<Alert status="info">
The scatter below maps each campaign by discount depth (x) and ROI (y).
Top-left = low discount, high return — the efficiency frontier.
Bottom-right = deep discount, poor return — margin destroyers.
</Alert>

<ScatterPlot
    data={promo_scatter_roi}
    x=discount_rate
    y=roi
    series=promo_type
    title="Promo Efficiency Frontier"
    subtitle="Top-left = low discount + high ROI (efficient). Bottom-right = margin destroyers."
    xAxisTitle="Discount Rate"
    yAxisTitle="ROI (Revenue per Discount VND)"
    xFmt="pct2"
    yFmt="0.0"
>
    <ReferenceLine x=0.15 label="15% Threshold" hideValue=true color=warning lineType=dashed/>
    <ReferenceLine y=5 label="5× ROI" hideValue=true color=positive lineType=dashed/>
</ScatterPlot>

## 3.5. Average Order Value by Category Scope

<Alert status="info">
AOV varies by category scope and promo type. Streetwear fixed discounts average <Value data={category_aov} column=avg_aov row=2 fmt=num0/> VND per order,
while Outdoor percentage campaigns average <Value data={category_aov} column=avg_aov row=1 fmt=num0/> VND.
Site-wide percentage promos sit at <Value data={category_aov} column=avg_aov row=0 fmt=num0/> VND.
These differences reflect category price points more than promo design.
</Alert>

<BarChart
    data={category_aov}
    x=category_scope
    y=avg_aov
    series=promo_type
    title="Average Order Value by Category Scope"
    subtitle="Category-restricted promos may drive higher basket sizes"
    yAxisTitle="AOV (VND)"
    yFmt="num0"
/>

## 4. Channel: Where Promo Dollars Work Hardest

<Alert status="info">
Channel performance reveals where promotional dollars work hardest.
Email and social typically have lower CAC; paid search and display require tighter ROI thresholds.
</Alert>

<BarChart
    data={channel_performance}
    x=promo_channel
    y=total_revenue
    series=promo_type
    title="Revenue by Channel and Promo Type"
    subtitle="Where promotional dollars work hardest"
    yAxisTitle="Net Revenue"
    yFmt="num0"
/>

## 5. What-If: Shift 10% of Percentage Budget to Fixed

<Alert status="info">
If 10% of the total percentage discount budget were shifted to fixed discounts,
revenue would change from <Value data={what_if_shift} column=current_return fmt=num0/> VND
(current fixed-return rate)
to <Value data={what_if_shift} column=new_return fmt=num0/> VND.
That is <Value data={what_if_shift} column=incremental_revenue fmt=num0/> VND additional revenue
(<Value data={what_if_shift} column=pct_lift fmt=pct2/> lift)
with the same promo spend.
</Alert>

<Grid cols=3>
    <BigValue
        data={what_if_shift}
        value=shifted_discount
        title="Discount Budget Shifted"
        fmt="num0"
    />
    <BigValue
        data={what_if_shift}
        value=incremental_revenue
        title="Incremental Revenue"
        fmt="num0"
    />
    <BigValue
        data={what_if_shift}
        value=pct_lift
        title="Revenue Lift"
        fmt="pct2"
    />
</Grid>

## The Verdict

<Alert status="positive">
<b>Action:</b> Expand fixed-discount campaigns for high-margin categories.
Cap percentage discounts at 15%. Test category-specific fixed discounts instead of site-wide percentage sales.
Every VND of fixed discount generates <Value data={fixed_stats} column=roi fmt=0.0/>× revenue vs <Value data={pct_stats} column=roi fmt=0.0/>× for percentage —
a <b><Value data={roi_ratio} column=ratio fmt=0.0/>×</b> efficiency advantage.
See also <a href="/01-stories/marketing/03-cannibalization-test">Story 03: The Cannibalization Test</a> for pre/during/post campaign analysis.
</Alert>

## Deep Dive

- [Promotion Effectiveness](/02-eda/marketing/02-promotion-effectiveness)

