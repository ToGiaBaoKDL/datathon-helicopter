---
title: The Promo Paradox
---

# The Promo Paradox

<Alert status="warning">
<b>The question:</b> Why does the business run <Value data={pct_stats} column=campaigns fmt=0/> percentage-discount campaigns vs only <Value data={fixed_stats} column=campaigns fmt=0/> fixed-discount,
when fixed discounts deliver <b><Value data={roi_ratio} column=ratio fmt=0.0x/> higher ROI</b> per discount VND spent?
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

## 1. The Trade-off: Scale vs Efficiency

<Alert status="info">
Percentage: <Value data={pct_stats} column=campaigns fmt=0/> campaigns, <Value data={pct_stats} column=total_revenue fmt=num0/> VND revenue,
<Value data={pct_stats} column=avg_discount_rate fmt=pct2/> discount, <Value data={pct_stats} column=roi fmt=0.0x/> ROI.
Fixed: <Value data={fixed_stats} column=campaigns fmt=0/> campaigns, <Value data={fixed_stats} column=total_revenue fmt=num0/> VND revenue,
<Value data={fixed_stats} column=avg_discount_rate fmt=pct2/> discount, <Value data={fixed_stats} column=roi fmt=0.0x/> ROI. 
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
    <ReferenceLine x=0.20 label="20% Threshold" hideValue=true color=warning lineType=dashed/>
</BubbleChart>

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
    yFmt="0.0x"
/>

## 4. Channel: Where Promo Dollars Work Hardest

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

## The Verdict

<Alert status="positive">
<b>Action:</b> Expand fixed-discount campaigns for high-margin categories.
Cap percentage discounts at 15%. Test category-specific fixed discounts instead of site-wide percentage sales.
Every VND of fixed discount generates <Value data={fixed_stats} column=roi fmt=0.0x/> revenue vs <Value data={pct_stats} column=roi fmt=0.0x/> for percentage —
a <b><Value data={roi_ratio} column=ratio fmt=0.0x/></b> efficiency advantage.
</Alert>
