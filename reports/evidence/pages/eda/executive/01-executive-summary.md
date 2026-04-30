---
title: Executive Summary
---

One-page overview of top insights, risks, and recommended actions based on <Value data={dataset_meta} column=total_days fmt=num0/> days of operational data.

```sql dataset_meta
select count(*) as total_days from datathon_warehouse.mart_daily_executive_kpis
```

```sql revenue_cogs_profit_long
select sales_date, 'Revenue' as metric, revenue as value
from datathon_warehouse.mart_daily_executive_kpis
union all
select sales_date, 'COGS' as metric, cogs as value
from datathon_warehouse.mart_daily_executive_kpis
union all
select sales_date, 'Gross Profit' as metric, gross_profit as value
from datathon_warehouse.mart_daily_executive_kpis
order by sales_date
```

```sql _date_bounds
select sales_date from datathon_warehouse.mart_daily_executive_kpis
```

<DateRange
    name=date_range
    data={_date_bounds}
    dates=sales_date
/>

<AreaChart
    data={revenue_cogs_profit_long}
    x=sales_date
    y=value
    series=metric
    title="Revenue, COGS, and Gross Profit"
    subtitle="Executive overview of top-line, direct cost, and margin dollars over the full period"
    yAxisTitle="VND"
    yFmt="num0"
/>

```sql top_insights
with numbered as (
    select revenue, row_number() over (order by sales_date) as rn
    from datathon_warehouse.mart_daily_executive_kpis
    where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
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
    sum(total_revenue - total_cogs) / nullif(sum(total_revenue), 0) as avg_margin
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
    sum(case when avg_days_between_orders is null then 1 else 0 end)::int as single_order_customers,
    sum(case when recency_days > 2 * avg_days_between_orders then 1 else 0 end)::int as churned_customers,
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
    sum(total_net_revenue) / nullif(sum(total_discount_amount), 0) as roi,
    avg(discount_rate) as avg_discount_rate,
    count(*) as campaigns
from datathon_warehouse.mart_promotion_effectiveness
group by 1
order by roi desc
```

```sql promo_stats
select
    max(case when promo_type = 'fixed' then campaigns end) as fixed_campaigns,
    max(case when promo_type = 'fixed' then roi end) as fixed_roi,
    max(case when promo_type = 'percentage' then campaigns end) as pct_campaigns,
    max(case when promo_type = 'percentage' then roi end) as pct_roi
from (
    select
        promo_type,
        sum(total_net_revenue) / nullif(sum(total_discount_amount), 0) as roi,
        count(*) as campaigns
    from datathon_warehouse.mart_promotion_effectiveness
    group by 1
) t
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
  and sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
group by 1
order by 1
```

```sql conversion_peak
select
    max(case when avg_conversion = max_conv then year end) as peak_year,
    max(max_conv) as peak_conversion,
    min(case when avg_conversion = min_conv then year end) as trough_year,
    min(min_conv) as trough_conversion
from (
    select
        date_part('year', sales_date) as year,
        avg(session_to_order_rate) as avg_conversion,
        max(avg(session_to_order_rate)) over () as max_conv,
        min(avg(session_to_order_rate)) over () as min_conv
    from datathon_warehouse.mart_daily_executive_kpis
    where sessions > 0
      and sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
    group by 1
) t
```

```sql margin_peak
select
    max(case when avg_margin = max_margin then year end) as peak_year,
    max(max_margin) as peak_margin,
    min(case when avg_margin = min_margin then year end) as trough_year,
    min(min_margin) as trough_margin
from (
    select
        date_part('year', sales_date) as year,
        avg(gross_margin_rate) as avg_margin,
        max(avg(gross_margin_rate)) over () as max_margin,
        min(avg(gross_margin_rate)) over () as min_margin
    from datathon_warehouse.mart_daily_executive_kpis
    where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
    group by 1
) t
```

```sql retention_m1
select avg(retention_rate) as m1_retention
from datathon_warehouse.mart_monthly_customer_cohort
where months_since_first_order = 1
```

```sql return_overall
select avg(return_record_rate) as avg_return_rate
from datathon_warehouse.mart_daily_executive_kpis
```

```sql negative_margin_count
select count(*) as negative_margin_products
from datathon_warehouse.mart_product_lifetime_performance
where realized_margin_rate < 0 and lifecycle_stage != 'never_sold'
```

```sql revenue_peak
select
    date_part('year', sales_date) as peak_year,
    avg(revenue) as peak_avg_revenue
from datathon_warehouse.mart_daily_executive_kpis
where sessions > 0
  and sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
group by 1
order by peak_avg_revenue desc
limit 1
```

## Top 5 Insights

<Alert status="info">
<b>1. Revenue Direction</b>: Long-term trend is <Value data={top_insights} column=direction/> 
(<Value data={top_insights} column=daily_change fmt=num0/> VND/day slope, R² = <Value data={top_insights} column=r2 fmt=pct2/>).
<br/><i>Revenue peaked in <Value data={revenue_peak} column=peak_year/> at <Value data={revenue_peak} column=peak_avg_revenue fmt=num0/> VND/day average, then declined through 2020–2021.</i>
</Alert>

<Alert status="info">
<b>2. Best Channel</b>: <Value data={best_channel} column=acquisition_channel/> 
generates <Value data={best_channel} column=revenue_pct fmt=pct2/> of revenue 
with <Value data={best_channel} column=avg_margin fmt=pct2/> margin.
</Alert>

<Alert status="info">
<b>3. Customer Health</b>: <Value data={customer_health} column=active_pct fmt=pct2/> active, 
<Value data={customer_health} column=at_risk_pct fmt=pct2/> at-risk, 
<Value data={customer_health} column=churned_pct fmt=pct2/> churned, 
<Value data={customer_health} column=single_order_pct fmt=pct2/> single-order only.
<br/><i>The biggest opportunity: <Value data={customer_health} column=single_order_customers fmt=num0/> single-order customers (<Value data={customer_health} column=single_order_pct fmt=pct2/>) never returned.</i>
</Alert>

<Alert status="info">
<b>4. Operational Risk</b>: Last 30 days avg <Value data={operational_risk} column=avg_stockout fmt=0.00/> stockout days, 
<Value data={operational_risk} column=avg_delivery_days fmt=0.0/> delivery days.
<br/><i>Delivery is stable. Operations are not the bottleneck.</i>
</Alert>

<Alert status="info">
<b>5. Promotion ROI</b>: <Value data={promo_roi} column=promo_type/> promos yield highest ROI 
(<Value data={promo_roi} column=roi fmt=0.0/>× revenue per discount VND).
<br/><i>Fixed promos (<Value data={promo_stats} column=fixed_campaigns fmt=0/> campaigns) achieve <Value data={promo_stats} column=fixed_roi fmt=0.0/>× ROI vs <Value data={promo_stats} column=pct_roi fmt=0.0/>× for percentage promos (<Value data={promo_stats} column=pct_campaigns fmt=0/> campaigns).</i>
</Alert>

## Top 5 Risks

<Alert status="warning">
<b>1. Conversion Collapse</b>: Session-to-order rate peaked at <Value data={conversion_peak} column=peak_conversion fmt=pct2/> in <Value data={conversion_peak} column=peak_year/> and fell to <Value data={conversion_peak} column=trough_conversion fmt=pct2/> in <Value data={conversion_peak} column=trough_year/>.
Traffic is flat; capture is broken.
</Alert>

<Alert status="warning">
<b>2. Conversion Drop Flags</b>: <Value data={risk_flags} column=conversion_drop_days/> days in last 30 
below the p10 threshold.
<br/><i>Action: Audit checkout flow, page load speed, and mobile experience.</i>
</Alert>

<Alert status="warning">
<b>3. Return Spike</b>: <Value data={risk_flags} column=return_spike_days/> days in last 30 
with return rate above p95.
<br/><i>Action: Inspect return reasons — "defective" and "wrong_size" are fixable.</i>
</Alert>

<Alert status="warning">
<b>4. Margin Volatility</b>: Gross margin peaked at <Value data={margin_peak} column=peak_margin fmt=pct2/> in <Value data={margin_peak} column=peak_year/> and troughed at <Value data={margin_peak} column=trough_margin fmt=pct2/> in <Value data={margin_peak} column=trough_year/>.
<Value data={negative_margin_count} column=negative_margin_products fmt=0/> products have negative realized margin due to deep discounting.
</Alert>

<Alert status="warning">
<b>5. Cohort Quality</b>: Month-1 retention is <Value data={retention_m1} column=m1_retention fmt=pct2/>.
Most customers never return after their first purchase.
</Alert>

## Recommended Actions

<Alert status="positive">
<b>Fix Conversion (Priority #1)</b>: Conversion fell from <Value data={conversion_peak} column=peak_conversion fmt=pct2/> to <Value data={conversion_peak} column=trough_conversion fmt=pct2/>.
A +1pp lift would project massive incremental revenue at current traffic.
</Alert>

<Alert status="positive">
<b>Re-engage Single-Order Customers</b>: <Value data={customer_health} column=single_order_customers fmt=num0/> customers bought once and never returned. 
Send a time-limited "second purchase" offer within 30 days of first order.
</Alert>

<Alert status="positive">
<b>Optimize Promo Mix</b>: Fixed promos deliver <Value data={promo_stats} column=fixed_roi fmt=0.0/>× ROI vs <Value data={promo_stats} column=pct_roi fmt=0.0/>× for percentage.
Test expanding fixed-discount campaigns.
</Alert>

<Alert status="positive">
<b>Shift Ad Spend to Weekdays</b>: Wednesday outperforms Saturday in conversion and revenue.
Reallocate weekend budget to Tue–Thu.
</Alert>

<Alert status="positive">
<b>Reduce Return Rate</b>: Average return rate is <Value data={return_overall} column=avg_return_rate fmt=pct2/>.
Focus on "defective" and "wrong_size" root causes.
</Alert>

## Trend Detail

<LineChart
    data={trend_summary}
    x=year
    y=avg_conversion
    title="Annual Conversion Rate Trend"
    subtitle="Demand capture efficiency collapsed after 2013"
    yAxisTitle="Conversion Rate"
    xAxisTitle="Year"
    yFmt="pct2"
/>

<Alert status="info">
Conversion peaked at <Value data={conversion_peak} column=peak_conversion fmt=pct2/> in <Value data={conversion_peak} column=peak_year/> 
and troughed at <Value data={conversion_peak} column=trough_conversion fmt=pct2/> in <Value data={conversion_peak} column=trough_year/>.
</Alert>

<DataTable data={trend_summary} rows=15>
    <Column id=year title="Year" fmt=0/>
    <Column id=avg_revenue title="Avg Revenue" fmt=num0/>
    <Column id=avg_margin title="Margin" fmt=pct2/>
    <Column id=avg_conversion title="Conversion" fmt=pct2/>
    <Column id=avg_return_rate title="Return Rate" fmt=pct2/>
</DataTable>

## Related Stories

- [Revenue Anatomy](/stories/finance/01-revenue-anatomy)

