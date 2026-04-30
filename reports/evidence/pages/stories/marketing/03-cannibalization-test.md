---
title: The Cannibalization Test
---

<Alert status="warning">
<b>The question:</b> Do promotions pull forward demand that would have happened anyway? 
What happens to revenue <b>before, during, and after</b> campaigns?
</Alert>

```sql aggregate_windows
select
    period_type,
    round(sum(avg_daily_revenue * days_in_period)::double / sum(days_in_period), 0) as avg_daily_revenue,
    round(sum(avg_daily_orders * days_in_period)::double / sum(days_in_period), 0) as avg_daily_orders,
    count(distinct promo_id) as promo_count
from datathon_warehouse.mart_promo_cannibalization
group by 1
order by case period_type when 'pre' then 1 when 'during' then 2 when 'post' then 3 end
```

```sql by_type_windows
select
    promo_type,
    period_type,
    round(sum(avg_daily_revenue * days_in_period)::double / sum(days_in_period), 0) as avg_daily_revenue,
    round(sum(avg_daily_orders * days_in_period)::double / sum(days_in_period), 0) as avg_daily_orders
from datathon_warehouse.mart_promo_cannibalization
group by 1, 2
order by promo_type, case period_type when 'pre' then 1 when 'during' then 2 when 'post' then 3 end
```

```sql fixed_promo_impact
select
    period_type,
    round(sum(avg_daily_revenue * days_in_period)::double / sum(days_in_period), 0) as avg_daily_revenue
from datathon_warehouse.mart_promo_cannibalization
where promo_type = 'fixed'
group by 1
order by case period_type when 'pre' then 1 when 'during' then 2 when 'post' then 3 end
```

```sql pct_promo_impact
select
    period_type,
    round(sum(avg_daily_revenue * days_in_period)::double / sum(days_in_period), 0) as avg_daily_revenue
from datathon_warehouse.mart_promo_cannibalization
where promo_type = 'percentage'
group by 1
order by case period_type when 'pre' then 1 when 'during' then 2 when 'post' then 3 end
```

```sql promo_efficiency
select
    promo_type,
    round(avg(total_net_revenue), 0) as avg_revenue,
    round(avg(discount_rate), 4) as avg_discount_rate,
    count(*) as campaign_count
from datathon_warehouse.mart_promotion_effectiveness
where total_net_revenue > 0
group by 1
```

```sql fixed_lift_drop
select
    round(
        (select avg_daily_revenue from ${fixed_promo_impact} where period_type = 'during')
        / nullif((select avg_daily_revenue from ${fixed_promo_impact} where period_type = 'pre'), 0) - 1,
        4
    ) as during_lift,
    round(
        (select avg_daily_revenue from ${fixed_promo_impact} where period_type = 'post')
        / nullif((select avg_daily_revenue from ${fixed_promo_impact} where period_type = 'pre'), 0) - 1,
        4
    ) as post_drop
```

## 1. Aggregate Windows: No Obvious Cannibalization

<Alert status="info">
At the aggregate level, pre-period revenue (<b><Value data={aggregate_windows} column=avg_daily_revenue row=0 fmt=num0/></b> VND/day) and during-period revenue (<b><Value data={aggregate_windows} column=avg_daily_revenue row=1 fmt=num0/></b>) are nearly identical. 
Post-period actually <b>rises</b> to <Value data={aggregate_windows} column=avg_daily_revenue row=2 fmt=num0/> — suggesting no aggregate pull-forward.
</Alert>

<BarChart
    data={aggregate_windows}
    x=period_type
    y=avg_daily_revenue
    title="Average Daily Revenue by Promo Window"
    subtitle="Aggregate: pre, during, and post 14-day windows"
    yAxisTitle="Revenue (VND/day)"
    yFmt="num0"
/>

## 2. By Promo Type: Fixed Shows Clear Cannibalization

<Alert status="info">
The aggregate mask hides a critical split. <b>Fixed</b> discounts show a post-period <b>collapse</b> — revenue drops from pre to post. 
<b>Percentage</b> discounts show no such pattern. The high ROI of fixed promos masks a hidden cost: demand is pulled forward, not created.
</Alert>

<BarChart
    data={by_type_windows}
    x=period_type
    y=avg_daily_revenue
    series=promo_type
    title="Revenue by Window and Promo Type"
    subtitle="Fixed promos cannibalize; percentage promos sustain"
    yAxisTitle="Revenue (VND/day)"
    yFmt="num0"
/>

## 3. Fixed-Promo Math: During Change vs Post Drop

<Alert status="info">
Fixed promos: during-period revenue <b>falls <Value data={fixed_lift_drop} column=during_lift fmt=pct2/></b> vs pre.
Post-period drops by <b><Value data={fixed_lift_drop} column=post_drop fmt=pct2/></b> vs pre.
Revenue declines in both windows — the promo does not create demand, it only shifts timing.
</Alert>

<Grid cols=2>
    <BigValue
        data={fixed_lift_drop}
        value=during_lift
        title="Fixed: During Change vs Pre"
        fmt="pct2"
    />
    <BigValue
        data={fixed_lift_drop}
        value=post_drop
        title="Fixed: Post Drop vs Pre"
        fmt="pct2"
    />
</Grid>

## 4. Efficiency Context: Why Fixed Looks Good on Paper

<Alert status="info">
Fixed campaigns have a much lower discount rate (<b><Value data={promo_efficiency} column=avg_discount_rate row=0 fmt=pct2/></b>) than percentage (<b><Value data={promo_efficiency} column=avg_discount_rate row=1 fmt=pct2/></b>). 
But with only <Value data={promo_efficiency} column=campaign_count row=0 fmt=0/> fixed campaigns vs <Value data={promo_efficiency} column=campaign_count row=1 fmt=0/> percentage, the sample is small.
</Alert>

<BarChart
    data={promo_efficiency}
    x=promo_type
    y=avg_discount_rate
    title="Average Discount Rate by Promo Type"
    subtitle="Fixed = lower discount depth"
    yAxisTitle="Discount Rate"
    yFmt="pct2"
/>

<BarChart
    data={promo_efficiency}
    x=promo_type
    y=avg_revenue
    title="Average Revenue per Campaign"
    subtitle="Percentage campaigns drive more absolute revenue"
    yAxisTitle="Revenue (VND)"
    yFmt="num0"
/>

## The Verdict

<Alert status="info">
<b>Caveat:</b> Only <Value data={promo_efficiency} column=campaign_count row=0 fmt=0/> fixed campaigns exist in the dataset vs <Value data={promo_efficiency} column=campaign_count row=1 fmt=0/> percentage campaigns.
The post-period collapse for fixed promos is directionally suggestive but based on a small sample — confirm with A/B testing before reallocating budget.
</Alert>

<Alert status="positive">
<b>Action:</b> Fixed-discount promos show signs of cannibalizing future demand. Reduce fixed-promo frequency or extend campaign windows to smooth the post-period collapse.
Percentage promos do not show cannibalization — use them for sustained demand generation.
The true ROI of fixed promos must subtract the post-period revenue loss.
See also <a href="/stories/marketing/02-promo-paradox">Story 02: The Promo Paradox</a> for fixed vs percentage efficiency comparison.
</Alert>

## Deep Dive

- [Promotion Effectiveness](/eda/marketing/02-promotion-effectiveness)

