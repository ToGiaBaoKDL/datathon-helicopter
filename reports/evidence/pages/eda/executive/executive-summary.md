---
title: Executive Summary
---

# Executive Summary

One-page overview of top insights, risks, and recommended actions.

```sql top_insights
select
    'Revenue Trend' as insight,
    case
        when regr_slope(revenue, rn) > 100000 then 'Growing strongly'
        when regr_slope(revenue, rn) > 0 then 'Slightly growing'
        when regr_slope(revenue, rn) > -100000 then 'Slightly declining'
        else 'Declining'
    end as direction,
    abs(regr_slope(revenue, rn)) as daily_change,
    regr_r2(revenue, rn) as r2
from (
    select revenue, row_number() over (order by sales_date) as rn
    from datathon_warehouse.mart_daily_executive_kpis
)
```

```sql best_channel
select
    acquisition_channel,
    sum(total_revenue) as channel_revenue,
    sum(total_revenue) * 100.0 / sum(sum(total_revenue)) over () as revenue_pct,
    avg(total_revenue - total_cogs) / nullif(avg(total_revenue), 0) as avg_margin
from datathon_warehouse.mart_customer_rfm
group by 1
order by channel_revenue desc
limit 1
```

```sql customer_health
select
    sum(case when recency_days <= avg_days_between_orders then 1 else 0 end) as active_count,
    sum(case when recency_days > 2 * avg_days_between_orders then 1 else 0 end) as churned_count,
    count(*) as total_customers,
    active_count * 100.0 / total_customers as active_pct,
    churned_count * 100.0 / total_customers as churned_pct
from datathon_warehouse.mart_customer_rfm
where avg_days_between_orders is not null
```

```sql operational_risk
with max_date as (select max(sales_date) as d from datathon_warehouse.mart_daily_executive_kpis)
select
    avg(avg_stockout_days) as avg_stockout,
    avg(avg_days_to_deliver) as avg_delivery_days,
    max(avg_stockout_days) as max_stockout
from datathon_warehouse.mart_daily_executive_kpis
cross join max_date
where sales_date >= max_date.d - interval '30 days'
```

```sql risk_flags
with max_date as (select max(sales_date) as d from datathon_warehouse.mart_daily_risk_flags)
select
    sum(stockout_risk_flag) as stockout_days,
    sum(return_spike_flag) as return_spike_days,
    sum(conversion_drop_flag) as conversion_drop_days,
    count(*) as total_days
from datathon_warehouse.mart_daily_risk_flags
cross join max_date
where sales_date >= max_date.d - interval '30 days'
```

```sql revenue_decline_streak
with max_date as (select max(sales_date) as d from datathon_warehouse.mart_daily_executive_kpis)
select
    count(*) as decline_days
from (
    select
        sales_date,
        revenue,
        avg(revenue) over () as overall_avg,
        case when revenue < overall_avg then 1 else 0 end as below_avg
    from datathon_warehouse.mart_daily_executive_kpis
    cross join max_date
    where sales_date >= max_date.d - interval '30 days'
)
where below_avg = 1
```

```sql promo_roi
select
    promo_type,
    avg(total_net_revenue / nullif(total_discount_amount, 0)) as roi,
    avg(discount_rate) as avg_discount_rate,
    count(*) as campaigns
from datathon_warehouse.mart_promotion_effectiveness
group by 1
order by roi desc
```

```sql revenue_decline_streak
select
    count(*) as decline_days
from (
    select
        sales_date,
        revenue,
        avg(revenue) over () as overall_avg,
        case when revenue < overall_avg then 1 else 0 end as below_avg
    from datathon_warehouse.mart_daily_executive_kpis
    where sales_date >= current_date - interval '30 days'
)
where below_avg = 1
```

## Top 5 Insights

<Alert status="info">
<b>1. Revenue Direction</b>: <Value data={top_insights} column=direction/> 
(<Value data={top_insights} column=daily_change fmt=num0/> VND/day slope, R² = <Value data={top_insights} column=r2 fmt=pct1/>).
<br/><i>If declining, investigate traffic and conversion drivers.</i>
</Alert>

<Alert status="info">
<b>2. Best Channel</b>: <Value data={best_channel} column=acquisition_channel/> 
generates <Value data={best_channel} column=revenue_pct fmt=pct1/> of revenue 
with <Value data={best_channel} column=avg_margin fmt=pct1/> margin.
<br/><i>Double down on this channel; reduce spend on underperformers.</i>
</Alert>

<Alert status="info">
<b>3. Customer Health</b>: <Value data={customer_health} column=active_pct fmt=pct1/> active, 
<Value data={customer_health} column=churned_pct fmt=pct1/> churned.
<br/><i>Churned customers represent a win-back opportunity pool.</i>
</Alert>

<Alert status="info">
<b>4. Operational Risk</b>: Avg <Value data={operational_risk} column=avg_stockout fmt=0.00/> stockout days, 
<Value data={operational_risk} column=avg_delivery_days fmt=0.0/> delivery days.
<br/><i>Watch stockout — max reached <Value data={operational_risk} column=max_stockout fmt=0.00/> days.</i>
</Alert>

<Alert status="info">
<b>5. Promotion ROI</b>: <Value data={promo_roi} column=promo_type/> promos yield highest ROI 
(<Value data={promo_roi} column=roi fmt=0.0x/> revenue per discount VND).
<br/><i>Shift promo mix toward higher-ROI campaign types.</i>
</Alert>

## Top 5 Risks

<Alert status="warning">
<b>1. Stockout Risk</b>: <Value data={risk_flags} column=stockout_days/> days in last 30 
(<Value data={risk_flags} column=stockout_days/>/<Value data={risk_flags} column=total_days/>).
<br/><i>Action: Review reorder points and supplier lead times.</i>
</Alert>

<Alert status="warning">
<b>2. Return Spike</b>: <Value data={risk_flags} column=return_spike_days/> days in last 30 
with return rate above p95.
<br/><i>Action: Inspect return reasons — defective and late_delivery are fixable.</i>
</Alert>

<Alert status="warning">
<b>3. Conversion Drop</b>: <Value data={risk_flags} column=conversion_drop_days/> days in last 30 
with conversion below p10.
<br/><i>Action: Check for website outages, checkout friction, or ad spend waste.</i>
</Alert>

<Alert status="warning">
<b>4. Revenue Decline</b>: <Value data={revenue_decline_streak} column=decline_days/> of last 30 days 
below historical average.
<br/><i>Action: Diagnose whether demand (traffic) or supply (inventory) is the constraint.</i>
</Alert>

<Alert status="warning">
<b>5. Margin Pressure</b>: 359 products have negative realized margin (COGS > net revenue).
<br/><i>Action: Audit deep-discount campaigns and product mix.</i>
</Alert>

## Recommended Actions

<Alert status="positive">
<b>Focus</b>: Allocate 60% of acquisition budget to <Value data={best_channel} column=acquisition_channel/> — 
it drives <Value data={best_channel} column=revenue_pct fmt=pct1/> of revenue with the best margin.
</Alert>

<Alert status="positive">
<b>Fix</b>: Address inventory risk on <Value data={risk_flags} column=stockout_days/> days. 
Increase safety stock for top 20 SKUs by revenue.
</Alert>

<Alert status="positive">
<b>Re-engage</b>: Launch win-back email for <Value data={customer_health} column=churned_count fmt=num0/> 
churned customers with a personalized offer based on their last purchase category.
</Alert>

<Alert status="positive">
<b>Optimize</b>: Shift promo mix toward <Value data={promo_roi} column=promo_type/> campaigns. 
Current ROI: <Value data={promo_roi} column=roi fmt=0.0x/> revenue per discount VND.
</Alert>

<Alert status="positive">
<b>Monitor</b>: Watch conversion rate daily. <Value data={risk_flags} column=conversion_drop_days/> 
drops below p10 in the last 30 days signal demand-capture issues.
</Alert>
