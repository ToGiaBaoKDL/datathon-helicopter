---
title: Executive Summary
---

# Executive Summary

One-page overview of top insights, risks, and recommended actions based on 3,833 days of operational data.

```sql top_insights
with numbered as (
    select revenue, row_number() over (order by sales_date) as rn
    from datathon_warehouse.mart_daily_executive_kpis
)
select
    case
        when regr_slope(revenue, rn) > 100000 then 'Growing strongly'
        when regr_slope(revenue, rn) > 0 then 'Slightly growing'
        when regr_slope(revenue, rn) > -100000 then 'Slightly declining'
        else 'Declining'
    end as direction,
    abs(regr_slope(revenue, rn)) as daily_change,
    regr_r2(revenue, rn) as r2
from numbered
```

```sql best_channel
select
    acquisition_channel,
    sum(total_revenue) as channel_revenue,
    sum(total_revenue) / sum(sum(total_revenue)) over () as revenue_pct,
    avg(total_revenue - total_cogs) / nullif(avg(total_revenue), 0) as avg_margin
from datathon_warehouse.mart_customer_rfm
group by 1
order by channel_revenue desc
limit 1
```

```sql customer_health
select
    sum(case when recency_days <= avg_days_between_orders then 1 else 0 end)::double / count(*) as active_pct,
    sum(case when recency_days > 2 * avg_days_between_orders then 1 else 0 end)::double / count(*) as churned_pct,
    sum(case when avg_days_between_orders is not null and recency_days > avg_days_between_orders and recency_days <= 2 * avg_days_between_orders then 1 else 0 end)::double / count(*) as at_risk_pct,
    sum(case when avg_days_between_orders is null then 1 else 0 end)::double / count(*) as single_order_pct,
    count(*) as total_customers
from datathon_warehouse.mart_customer_rfm
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

```sql trend_summary
select
    date_part('year', sales_date) as year,
    avg(revenue) as avg_revenue,
    avg(gross_margin_rate) as avg_margin,
    avg(session_to_order_rate) as avg_conversion,
    avg(return_record_rate) as avg_return_rate
from datathon_warehouse.mart_daily_executive_kpis
where sessions > 0
group by 1
order by 1
```

## Top 5 Insights

<Alert status="info">
<b>1. Revenue Direction</b>: Long-term trend is <Value data={top_insights} column=direction/> 
(<Value data={top_insights} column=daily_change fmt=num0/> VND/day slope, R² = <Value data={top_insights} column=r2 fmt=pct1/>).
<br/><i>Revenue peaked in 2016 (~5.8M/day) then declined to ~2.9M in 2020–2021. The trend is weakly negative with high volatility.</i>
</Alert>

<Alert status="info">
<b>2. Best Channel</b>: <Value data={best_channel} column=acquisition_channel/> 
generates <Value data={best_channel} column=revenue_pct fmt=pct1/> of revenue 
with <Value data={best_channel} column=avg_margin fmt=pct1/> margin.
<br/><i>However, all channels are within 1pp in margin (13.6–13.9%) — the business is not channel-dependent for profitability.</i>
</Alert>

<Alert status="info">
<b>3. Customer Health</b>: <Value data={customer_health} column=active_pct fmt=pct1/> active, 
<Value data={customer_health} column=at_risk_pct fmt=pct1/> at-risk, 
<Value data={customer_health} column=churned_pct fmt=pct1/> churned, 
<Value data={customer_health} column=single_order_pct fmt=pct1/> single-order only.
<br/><i>The biggest opportunity is converting single-order customers (22,358 customers, ~25%) to repeat buyers before they go cold.</i>
</Alert>

<Alert status="info">
<b>4. Operational Risk</b>: Avg <Value data={operational_risk} column=avg_stockout fmt=0.00/> stockout days, 
<Value data={operational_risk} column=avg_delivery_days fmt=0.0/> delivery days.
<br/><i>Stockout has improved from 1.36 (2012) to 1.09 (2022). Delivery is stable at ~6 days. Operations are not the bottleneck.</i>
</Alert>

<Alert status="info">
<b>5. Promotion ROI</b>: <Value data={promo_roi} column=promo_type/> promos yield highest ROI 
(<Value data={promo_roi} column=roi fmt=0.0x/> revenue per discount VND) but only 5 campaigns.
<br/><i>Percentage promos (45 campaigns) have lower ROI (7.2x) but much higher scale. Discount rate averages 12.9% vs 1.2% for fixed.</i>
</Alert>

## Top 5 Risks

<Alert status="warning">
<b>1. Conversion Collapse</b>: Session-to-order rate fell from 1.2% (2013) to 0.3% (2022) — a 75% decline. 
This is the single biggest threat to revenue. Traffic is flat; capture is broken.
</Alert>

<Alert status="warning">
<b>2. Conversion Drop Flags</b>: <Value data={risk_flags} column=conversion_drop_days/> days in last 30 
below the p10 threshold.
<br/><i>Action: Audit checkout flow, page load speed, and mobile experience. The decline is structural, not seasonal.</i>
</Alert>

<Alert status="warning">
<b>3. Return Spike</b>: <Value data={risk_flags} column=return_spike_days/> days in last 30 
with return rate above p95.
<br/><i>Action: Inspect return reasons — "defective" and "wrong_size" are fixable with supplier QC and sizing guides.</i>
</Alert>

<Alert status="warning">
<b>4. Margin Volatility</b>: Gross margin swings from 8% (2021) to 21% (2012) with no clear pattern. 
359 products have negative realized margin due to deep discounting.
</Alert>

<Alert status="warning">
<b>5. Cohort Quality</b>: Month-1 retention is only ~3.5%. Most customers never return after their first purchase. 
The business is essentially running a continuous acquisition treadmill.
</Alert>

## Recommended Actions

<Alert status="positive">
<b>Fix Conversion (Priority #1)</b>: A +1 percentage point conversion uplift projects ~150% revenue increase (~6.4M incremental/day at current averages). 
Focus on: mobile checkout friction, page load speed, and payment method coverage.
</Alert>

<Alert status="positive">
<b>Re-engage Single-Order Customers</b>: 22,358 customers bought once and never returned. 
Send a time-limited "second purchase" offer within 30 days of first order.
</Alert>

<Alert status="positive">
<b>Optimize Promo Mix</b>: Fixed-discount campaigns have 11× higher ROI than percentage (82x vs 7.2x) but only 5 campaigns ran. 
Test expanding fixed-discount promos for high-margin categories.
</Alert>

<Alert status="positive">
<b>Shift Ad Spend to Weekdays</b>: Wednesday has the highest conversion (0.78%) and revenue (~4.7M). 
Saturday is the weakest (0.67%, ~3.9M). Reallocate weekend budget to Tue–Thu.
</Alert>

<Alert status="positive">
<b>Reduce Return Rate</b>: ~5.5% of orders have returns. Focus on "defective" and "wrong_size" root causes — 
these are controllable unlike "changed_mind".
</Alert>

## Trend Detail

<DataTable data={trend_summary} rows=15 />
