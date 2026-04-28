---
title: The Discount Calendar Ritual
---

# The Discount Calendar Ritual

<Alert status="warning">
<b>The question:</b> Every year the business runs the same percentage promos at the same <Value data={percentage_discount} column=avg_pct_discount fmt=pct2/> average discount. 
Revenue from these campaigns has fallen <Value data={revenue_drop} column=revenue_drop_pct fmt=pct2/> since 2013. 
Is the discount calendar a revenue engine or a margin ritual?
</Alert>

```sql promo_trend
select
    date_part('year', start_date)::int as year,
    promo_type,
    count(*) as campaigns,
    round(avg(discount_rate), 4) as avg_discount,
    round(sum(total_net_revenue), 0) as total_revenue,
    round(sum(total_discount_amount), 0) as total_discount
from datathon_warehouse.mart_promotion_effectiveness
where total_orders > 0
group by 1, 2
order by year, promo_type
```

```sql promo_summary
select
    promo_type,
    count(*) as campaigns,
    round(avg(discount_rate), 4) as avg_discount,
    round(sum(total_net_revenue), 0) as total_revenue,
    round(sum(total_discount_amount), 0) as total_discount,
    round(sum(total_discount_amount)::double / nullif(sum(total_net_revenue + total_discount_amount), 0), 4) as effective_discount
from datathon_warehouse.mart_promotion_effectiveness
where total_orders > 0
group by 1
order by total_revenue desc
```

```sql percentage_discount
select round(avg(discount_rate), 4) as avg_pct_discount
from datathon_warehouse.mart_promotion_effectiveness
where promo_type = 'percentage'
  and total_orders > 0
```

```sql revenue_drop
select
    round(
        (sum(case when year = 2022 then total_revenue else 0 end) - sum(case when year = 2013 then total_revenue else 0 end))
        / nullif(sum(case when year = 2013 then total_revenue else 0 end), 0),
        4
    ) as revenue_drop_pct
from (
    select date_part('year', start_date)::int as year, sum(total_net_revenue) as total_revenue
    from datathon_warehouse.mart_promotion_effectiveness
    where total_orders > 0 and promo_type = 'percentage'
    group by 1
) t
```

```sql negative_by_category
select
    category,
    count(*) as total_skus,
    sum(case when realized_margin_rate < 0 then 1 else 0 end) as negative_skus,
    round(sum(case when realized_margin_rate < 0 then 1 else 0 end)::double / count(*), 4) as negative_pct,
    round(avg(realized_margin_rate), 4) as avg_margin
from datathon_warehouse.mart_product_lifetime_performance
where lifecycle_stage != 'never_sold'
group by 1
order by negative_pct desc
```

```sql category_discount_exposure
select
    coalesce(applicable_category, 'All Categories') as category,
    count(*) as campaigns,
    round(avg(discount_rate), 4) as avg_discount,
    round(sum(total_net_revenue), 0) as promo_revenue
from datathon_warehouse.mart_promotion_effectiveness
where total_orders > 0
group by 1
order by avg_discount desc
```

## 1. The Ritual: Same Discount, Every Year

<Alert status="info">
Percentage campaigns run like clockwork: <Value data={promo_summary} column=campaigns fmt=0/> campaigns, 
<Value data={promo_summary} column=avg_discount fmt=pct2/> discount, <Value data={promo_summary} column=total_revenue fmt=num0/> VND revenue. 
The discount rate has barely changed in a decade — a ritual, not a strategy.
</Alert>

<BarChart
    data={promo_trend}
    x=year
    y=avg_discount
    series=promo_type
    title="Average Discount Rate by Year and Promo Type"
    subtitle="Percentage discount is locked in a narrow band year after year"
    yAxisTitle="Discount Rate"
    yFmt="pct2"
/>

<AreaChart
    data={promo_trend}
    x=year
    y=total_revenue
    series=promo_type
    title="Promo Revenue by Year and Type"
    subtitle="Promo revenue is declining even as discount depth stays flat"
    yAxisTitle="Revenue (VND)"
    yFmt="num0"
/>

## 2. The Decline: Promo Revenue Is Falling

<Alert status="info">
Percentage promo revenue peaked in 2013–2015 and has declined since. 
The business is discounting at the same rate but generating less return — a classic diminishing-returns pattern.
</Alert>

<LineChart
    data={promo_trend}
    x=year
    y=total_revenue
    series=promo_type
    title="Promo Revenue Trend Over Time"
    subtitle="Percentage promo revenue peaked early and has declined since"
    yAxisTitle="Revenue (VND)"
    yFmt="num0"
/>

<Grid cols=2>
    <BigValue
        data={promo_summary}
        value=total_discount
        title="Total Discount Given"
        fmt="num0"
    />
    <BigValue
        data={promo_summary}
        value=effective_discount
        title="Effective Discount Rate"
        fmt="pct2"
    />
</Grid>

## 3. The Real Culprit: Product Margin, Not Promo Discount

<Alert status="info">
Streetwear has the highest share of loss-making SKUs (<Value data={negative_by_category} column=negative_pct fmt=pct2/>) 
but the lowest promo discount exposure. 
The margin problem is structural — pricing and COGS — not promotional.
</Alert>

<BarChart
    data={negative_by_category}
    x=category
    y=negative_pct
    title="Negative-Margin SKU Share by Category"
    subtitle="Streetwear leads in loss-making products despite low discount exposure"
    yAxisTitle="Share of SKU with Negative Margin"
    yFmt="pct2"
/>

<BarChart
    data={category_discount_exposure}
    x=category
    y=avg_discount
    title="Average Promo Discount by Category Scope"
    subtitle="Streetwear faces minimal discounting; All Categories promos dominate"
    yAxisTitle="Discount Rate"
    yFmt="pct2"
/>

## The Verdict

<Alert status="positive">
<b>Action:</b> The discount calendar is a ritual with diminishing returns. 
Percentage revenue has dropped <Value data={revenue_drop} column=revenue_drop_pct fmt=pct2/> since 2013 at the same discount depth. 
The margin crisis is not caused by discounting — it is caused by <Value data={negative_by_category} column=negative_skus fmt=0/> negative-margin SKUs, mostly in Streetwear. 
Cut the ritual: test lower discount rates (8–10%) or shift from site-wide percentage to category-specific fixed discounts. 
Fix pricing and COGS for Streetwear before blaming promotions.
</Alert>
