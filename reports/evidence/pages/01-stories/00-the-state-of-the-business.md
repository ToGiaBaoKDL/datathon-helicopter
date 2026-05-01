---
title: The State of the Business
---

Ten years of daily operations. Millions of orders. One question:

> *Where is the money really going, and what is the single biggest threat?*

This page distills the entire warehouse into the vital signs that matter — revenue, customers, inventory, promotions, quality, and seasonality — and connects each signal to the deeper story beneath it.

```sql _date_bounds
select sales_date from datathon_warehouse.mart_daily_executive_kpis
```

<DateRange
    name=date_range
    data={_date_bounds}
    dates=sales_date
/>

```sql vital_signs
select
    sum(revenue) as total_revenue,
    sum(gross_profit) as total_gross_profit,
    sum(gross_profit) / nullif(sum(revenue), 0) as overall_margin,
    avg(session_to_order_rate) as avg_conversion,
    sum(order_count) as total_orders,
    avg(return_record_rate) as avg_return_rate
from datathon_warehouse.mart_daily_executive_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
```

```sql revenue_trend
select
    sales_date,
    revenue,
    gross_profit,
    gross_margin_rate,
    session_to_order_rate,
    order_count
from datathon_warehouse.mart_daily_executive_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
order by sales_date
```

```sql revenue_peak
select
    date_part('year', sales_date) as year,
    avg(revenue) as avg_revenue
from datathon_warehouse.mart_daily_executive_kpis
where sessions > 0
  and sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
group by 1
order by avg_revenue desc
limit 1
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

```sql customer_health
select
    sum(case when recency_days <= avg_days_between_orders then 1 else 0 end)::double / count(*) as active_pct,
    sum(case when recency_days > 2 * avg_days_between_orders then 1 else 0 end)::double / count(*) as churned_pct,
    sum(case when avg_days_between_orders is null then 1 else 0 end)::double / count(*) as single_order_pct,
    sum(case when avg_days_between_orders is null then 1 else 0 end)::int as single_order_customers,
    count(*) as total_customers
from datathon_warehouse.mart_customer_rfm
```

```sql retention_m1
select avg(retention_rate) as m1_retention
from datathon_warehouse.mart_monthly_customer_cohort
where months_since_first_order = 1
```

```sql clv_pareto
with ranked as (
    select
        customer_id,
        total_revenue,
        ntile(10) over (order by total_revenue) as decile
    from datathon_warehouse.mart_customer_rfm
)
select
    sum(case when decile = 10 then total_revenue else 0 end)::double / sum(total_revenue) as top10_revenue_share,
    sum(case when decile >= 9 then total_revenue else 0 end)::double / sum(total_revenue) as top20_revenue_share
from ranked
```

```sql inventory_kpis
select
    avg(avg_days_of_supply) as avg_days_supply,
    avg(avg_sell_through_rate) as avg_sell_through,
    avg(stockout_product_count) as avg_stockout_products
from datathon_warehouse.mart_monthly_inventory_snapshot
```

```sql negative_margin_count
select count(*) as negative_margin_products
from datathon_warehouse.mart_product_lifetime_performance
where realized_margin_rate < 0 and lifecycle_stage != 'never_sold'
```

```sql never_sold_count
select count(*) as never_sold_products
from datathon_warehouse.mart_product_lifetime_performance
where lifecycle_stage = 'never_sold'
```

```sql promo_roi
select
    promo_type,
    sum(total_net_revenue) / nullif(sum(total_discount_amount), 0) as roi,
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

```sql cod_rates
select
    case when payment_method = 'cod' then 'COD' else 'Prepaid' end as payment_group,
    cast(sum(cancelled_lines) as double) / nullif(sum(order_line_count), 0) as cancellation_rate
from datathon_warehouse.mart_daily_payment_checkout_kpis
group by 1
order by payment_group
```

```sql cod_cancellation
select cancellation_rate from ${cod_rates} where payment_group = 'COD'
```

```sql prepaid_cancellation
select cancellation_rate from ${cod_rates} where payment_group = 'Prepaid'
```

```sql return_reasons
select
    'defective' as reason, sum(defective_return_count) as cnt
from datathon_warehouse.mart_daily_returns_kpis
union all
select 'wrong_size', sum(wrong_size_return_count)
from datathon_warehouse.mart_daily_returns_kpis
union all
select 'changed_mind', sum(changed_mind_return_count)
from datathon_warehouse.mart_daily_returns_kpis
union all
select 'not_as_described', sum(not_as_described_return_count)
from datathon_warehouse.mart_daily_returns_kpis
union all
select 'late_delivery', sum(late_delivery_return_count)
from datathon_warehouse.mart_daily_returns_kpis
order by cnt desc
```

```sql top_return_reason
select reason, cnt from ${return_reasons} order by cnt desc limit 1
```

```sql seasonal_index
select
    month,
    seasonal_index
from datathon_warehouse.mart_seasonal_pattern
order by month
```

```sql peak_trough_months
select
    max(case when seasonal_index = max_idx then month end) as peak_month,
    max(max_idx) as peak_index,
    min(case when seasonal_index = min_idx then month end) as trough_month,
    min(min_idx) as trough_index
from (
    select month, seasonal_index,
        max(seasonal_index) over () as max_idx,
        min(seasonal_index) over () as min_idx
    from datathon_warehouse.mart_seasonal_pattern
) t
```

```sql conversion_lift
select
    avg(session_to_order_rate) as current_conversion,
    avg(revenue) as avg_daily_revenue,
    avg(sessions) as avg_daily_sessions,
    (avg(session_to_order_rate) + 0.01) / nullif(avg(session_to_order_rate), 0) - 1 as lift_pct,
    avg(sessions) * (avg(session_to_order_rate) + 0.01) * (avg(revenue) / nullif(avg(order_count), 0)) - avg(revenue) as incremental_revenue_daily
from datathon_warehouse.mart_daily_executive_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
  and sessions > 0
  and order_count > 0
```

```sql risk_flags
select
    sum(stockout_risk_flag) as stockout_days,
    sum(return_spike_flag) as return_spike_days,
    sum(conversion_drop_flag) as conversion_drop_days,
    count(*) as total_days
from datathon_warehouse.mart_daily_risk_flags
```

```sql device_snapshot
select
    breakdown_value as device_type,
    avg(approx_conversion_rate) as avg_conversion_rate,
    sum(order_count) as total_orders
from datathon_warehouse.mart_daily_conversion_breakdown
where breakdown_type = 'device_type'
group by 1
order by avg_conversion_rate desc
```

```sql region_concentration
select
    region,
    total_revenue,
    total_revenue / sum(total_revenue) over () as revenue_share
from datathon_warehouse.mart_region_fulfillment_profile
order by total_revenue desc
limit 1
```

## The Vital Signs

<Alert status="info">
After <Value data={vital_signs} column=total_orders fmt=num0/> orders and <Value data={vital_signs} column=total_revenue fmt=num0/> VND in revenue, the numbers tell a story of a business that scaled — then stalled. The margin is <Value data={vital_signs} column=overall_margin fmt=pct2/>, conversion averages <Value data={vital_signs} column=avg_conversion fmt=pct2/>, and <Value data={vital_signs} column=avg_return_rate fmt=pct2/> of transactions come back as returns. The question is not whether there are problems. It is which problem to fix first.
</Alert>

<Grid cols=4>
    <BigValue
        data={vital_signs}
        value=total_revenue
        title="Total Revenue"
        fmt="num0"
    />
    <BigValue
        data={vital_signs}
        value=overall_margin
        title="Gross Margin"
        fmt="pct2"
    />
    <BigValue
        data={vital_signs}
        value=avg_conversion
        title="Avg Conversion"
        fmt="pct2"
    />
    <BigValue
        data={vital_signs}
        value=avg_return_rate
        title="Return Rate"
        fmt="pct2"
    />
</Grid>

## The Revenue Mask

<Alert status="warning">
Revenue peaked in <Value data={revenue_peak} column=year fmt=0/> at <Value data={revenue_peak} column=avg_revenue fmt=num0/> VND per day. But revenue is a lagging indicator. It masks the fact that demand capture — the ability to turn a visitor into a buyer — has collapsed.
</Alert>

<Alert status="info">
The 2019 cliff is the most dramatic event in the dataset: revenue dropped <b>-38.56%</b> year-over-year, and conversion fell <b>-40.24%</b>. The business never recovered its pre-2019 trajectory. Understanding what broke in 2019 is not historical curiosity — it is diagnostic necessity.
</Alert>

<AreaChart
    data={revenue_trend}
    x=sales_date
    y=revenue
    title="Daily Revenue Over Time"
    subtitle="The top line hides a structural fracture beneath"
    yAxisTitle="Revenue"
    yFmt="num0"
/>

<Alert status="positive">
<b>Deep Dive:</b> <a href="/01-stories/the-2019-cliff">The 2019 Cliff</a> dissects what broke, when, and why the recovery never came.
</Alert>

## The Conversion Crisis

<Alert status="warning">
Session-to-order rate peaked at <Value data={conversion_peak} column=peak_conversion fmt=pct2/> in <Value data={conversion_peak} column=peak_year/> and troughed at <Value data={conversion_peak} column=trough_conversion fmt=pct2/> in <Value data={conversion_peak} column=trough_year/>. That is a <b>three-quarters collapse</b> in demand capture efficiency.
</Alert>

<Alert status="info">
Traffic is not the problem. The business gets visitors. It simply fails to convert them. In 2013, roughly 1 in 85 sessions became an order. By 2021, it was 1 in 320. The funnel is leaking at the bottom, not the top.
</Alert>

<LineChart
    data={revenue_trend}
    x=sales_date
    y=session_to_order_rate
    title="Daily Conversion Rate Over Time"
    subtitle="The single most important metric in this dataset"
    yAxisTitle="Conversion Rate"
    yFmt="pct2"
>
    <ReferenceLine y=0.005 label="0.5% Target" hideValue=true color=positive lineType=dashed/>
</LineChart>

<Alert status="positive">
<b>Deep Dive:</b> <a href="/01-stories/marketing/01-demand-capture-crisis">The Demand Capture Crisis</a> explores why conversion died and what to audit first.
</Alert>

## The Customer Graveyard

<Alert status="warning">
<Value data={customer_health} column=single_order_customers fmt=num0/> customers — <Value data={customer_health} column=single_order_pct fmt=pct2/> of the entire base — bought once and never returned. This is not a retention problem. It is a <b>first-repeat failure</b>.
</Alert>

<Alert status="info">
Month-1 retention is <Value data={retention_m1} column=m1_retention fmt=pct2/>. For every 1,000 first-time buyers, roughly <Value data={retention_m1} column=m1_retention fmt=pct2/> come back in month one. The rest are gone. The business is running a customer acquisition treadmill with no retention flywheel.
</Alert>

<Alert status="info">
Revenue concentration is extreme: the top 10% of customers generate <Value data={clv_pareto} column=top10_revenue_share fmt=pct2/> of revenue, and the top 20% generate <Value data={clv_pareto} column=top20_revenue_share fmt=pct2/>. Losing a single Platinum customer costs more than acquiring ten Bronze ones.
</Alert>

<Alert status="positive">
<b>Deep Dives:</b>
- <a href="/01-stories/customer/01-retention-trap">The Retention Trap</a> — why customers leave after one purchase.
- <a href="/01-stories/customer/02-rfm-who-pays">RFM — Who Pays the Bills?</a> — the Pareto reality of customer value.
- <a href="/01-stories/customer/03-unit-economics-map">The Unit Economics Map</a> — which channels bring profitable customers.
</Alert>

## The Inventory Prison

<Alert status="warning">
The business carries <Value data={inventory_kpis} column=avg_days_supply fmt=0/> days of supply on average — nearly <b>three years</b> of inventory. Sell-through rate is <Value data={inventory_kpis} column=avg_sell_through fmt=pct2/>. Working capital is locked in products that barely move.
</Alert>

<Alert status="info">
<Value data={negative_margin_count} column=negative_margin_products fmt=0/> sold products have negative realized margin — every sale destroys value. And <Value data={never_sold_count} column=never_sold_products fmt=0/> SKUs have never generated a single order. The catalog is bloated.
</Alert>

<Alert status="positive">
<b>Deep Dives:</b>
- <a href="/01-stories/product/01-inventory-capital-trap">The Inventory Capital Trap</a> — quantifying the working capital drain.
- <a href="/01-stories/product/02-profitability-leak">The Profitability Leak</a> — where margin actually goes.
</Alert>

## The Quality Tax

<Alert status="warning">
Average return rate is <Value data={vital_signs} column=avg_return_rate fmt=pct2/>, with periodic spikes above 5%. The dominant return reason is <b><Value data={top_return_reason} column=reason/></b> (<Value data={top_return_reason} column=cnt fmt=num0/> cases) — a controllable operational failure.
</Alert>

<Alert status="info">
COD orders cancel at <b><Value data={cod_cancellation} column=cancellation_rate fmt=pct2/></b> vs <b><Value data={prepaid_cancellation} column=cancellation_rate fmt=pct2/></b> for prepaid — roughly <b><Value data={cod_cancellation} column=cancellation_rate fmt=0.0/>÷<Value data={prepaid_cancellation} column=cancellation_rate fmt=0.0/>×</b> the rate. Every cancelled COD order incurs packing and logistics routing costs with zero revenue. Prepayment commits the buyer at checkout; COD commits nothing.
</Alert>

<Alert status="info">
Risk flags paint a picture of daily instability: <Value data={risk_flags} column=stockout_days/> days flagged for stockout risk, <Value data={risk_flags} column=return_spike_days/> for return spikes, and <Value data={risk_flags} column=conversion_drop_days/> for conversion drops out of <Value data={risk_flags} column=total_days/> total days.
</Alert>

<Alert status="positive">
<b>Deep Dives:</b>
- <a href="/01-stories/product/03-quality-before-growth">Quality Before Growth</a> — why returns are a leading indicator of margin collapse.
- <a href="/01-stories/operations/02-cod-tax">The COD Tax</a> — the hidden cost of cash-on-delivery.
- <a href="/01-stories/operations/03-risk-flag-convergence">The Risk Flag Convergence</a> — when three warning systems trigger at once.
</Alert>

## The Promo Paradox

<Alert status="info">
Percentage promos (<Value data={promo_stats} column=pct_campaigns fmt=0/> campaigns) drive scale but at <Value data={promo_stats} column=pct_roi fmt=0.0/>× ROI. Fixed promos (<Value data={promo_stats} column=fixed_campaigns fmt=0/> campaigns) deliver <Value data={promo_stats} column=fixed_roi fmt=0.0/>× ROI — an <b>11.7× advantage</b> per discount VND. The business defaults to the less efficient format.
</Alert>

<Alert status="warning">
Fixed promos also show cannibalization: during-campaign revenue drops -28.85% and post-campaign drops -34.16%, meaning demand shifts rather than grows. Even the "better" promo type creates its own trap.
</Alert>

<Alert status="positive">
<b>Deep Dives:</b>
- <a href="/01-stories/marketing/02-promo-paradox">The Promo Paradox</a> — why fixed beats percentage and when it still fails.
- <a href="/01-stories/marketing/03-cannibalization-test">The Cannibalization Test</a> — do promos create demand or steal it?
</Alert>

## The Seasonal Truth

<Alert status="info">
Revenue does not peak in November–December. It peaks in <b>April–May</b> (seasonal index <Value data={peak_trough_months} column=peak_index fmt=0.00/>) and troughs in <b>November–December</b> (index <Value data={peak_trough_months} column=trough_index fmt=0.00/>). The business is anti-holiday.
</Alert>

<Alert status="warning">
This contradicts conventional retail wisdom. If marketing budget is concentrated in Q4 under the assumption of holiday demand, the business is fighting its own seasonality. Reallocate toward the true peak.
</Alert>

<BarChart
    data={seasonal_index}
    x=month
    y=seasonal_index
    sort=false
    title="Seasonal Revenue Index by Month"
    subtitle="1.0 = yearly average. The business peaks in spring, not winter"
    yAxisTitle="Index"
    yFmt="0.00"
>
    <ReferenceLine y=1 label="Yearly Average" hideValue=true color=info/>
    <ReferenceArea xMin=4 xMax=6 label="Peak Season" color=positive opacity=0.18/>
    <ReferenceArea xMin=11 xMax=12 label="Trough" color=warning opacity=0.18/>
</BarChart>

<Alert status="positive">
<b>Deep Dives:</b>
- <a href="/01-stories/marketing/04-seasonality-paradox">The Seasonality Paradox</a> — why the business is anti-holiday.
- <a href="/01-stories/marketing/05-discount-calendar-ritual">The Discount Calendar Ritual</a> — whether promo timing follows or fights seasonality.
</Alert>

## The Channel & Geography Snapshot

<Alert status="info">
<Value data={region_concentration} column=region/> generates <Value data={region_concentration} column=revenue_share fmt=pct2/> of total revenue — a concentration risk if logistics or competition hits that region. Geographic diversification is a strategic hedge.
</Alert>

<Alert status="info">
Acquisition channels are remarkably close in per-customer revenue, but intent quality varies. Direct and referral customers show higher retention than organic search and paid search. The highest-volume channel is not always the highest-value channel.
</Alert>

<Alert status="info">
Device conversion reveals a hidden pattern: mobile outperforms desktop, but tablet lags at roughly one-third the mobile rate. The "mobile-first" assumption is half-right — the real problem is tablet UX, not mobile.
</Alert>

<BarChart
    data={device_snapshot}
    x=device_type
    y=avg_conversion_rate
    title="Conversion Rate by Device"
    subtitle="Tablet is the true laggard, not mobile"
    yAxisTitle="Conversion Rate"
    yFmt="pct2"
>
    <ReferenceLine y=0.005 label="0.5% Target" hideValue=true color=positive lineType=dashed/>
</BarChart>

<Alert status="positive">
<b>Deep Dives:</b>
- <a href="/01-stories/marketing/06-device-blind-spot">The Device Blind Spot</a> — why tablet is the real conversion killer.
- <a href="/01-stories/operations/01-geographic-cost-puzzle">The Geographic Cost Puzzle</a> — margin paradox across regions.
- <a href="/01-stories/customer/03-unit-economics-map">The Unit Economics Map</a> — channel-level LTV and efficiency.
</Alert>

## The What-If: +1pp Conversion

<Alert status="info">
What would happen if conversion rose by just one percentage point — from <Value data={conversion_lift} column=current_conversion fmt=pct2/> to <Value data={conversion_lift} column=current_conversion fmt=pct2/> + 1pp?
</Alert>

<Alert status="positive">
At current traffic levels, a +1pp conversion lift would generate <b><Value data={conversion_lift} column=incremental_revenue_daily fmt=num0/> VND per day</b> — a <Value data={conversion_lift} column=lift_pct fmt=pct2/> revenue increase. That is <b>the highest-ROI lever in the entire business</b>. No new inventory, no new marketing spend, no new customers — just fixing the funnel.
</Alert>

<Grid cols=2>
    <BigValue
        data={conversion_lift}
        value=current_conversion
        title="Current Conversion"
        fmt="pct2"
    />
    <BigValue
        data={conversion_lift}
        value=lift_pct
        title="Revenue Lift from +1pp"
        fmt="pct2"
    />
</Grid>

## The Verdict: Priority Actions

<Alert status="positive">
<b>1. Fix Conversion First (Highest Impact)</b>
Conversion collapsed from <Value data={conversion_peak} column=peak_conversion fmt=pct2/> to <Value data={conversion_peak} column=trough_conversion fmt=pct2/>. Audit checkout flow, page load speed, mobile UX, and payment coverage. A +1pp lift projects <Value data={conversion_lift} column=incremental_revenue_daily fmt=num0/> VND/day in incremental revenue.
<br/><i>Owner:</i> Product + Engineering. <i>Timeline:</i> 30 days to audit, 60 days to ship fixes.
</Alert>

<Alert status="positive">
<b>2. Re-engage Single-Order Customers (Fast Win)</b>
<Value data={customer_health} column=single_order_customers fmt=num0/> customers bought once and vanished. Send a time-limited second-purchase offer within 30 days of first order.
<br/><i>Owner:</i> CRM + Marketing. <i>Timeline:</i> 14 days to launch.
</Alert>

<Alert status="positive">
<b>3. Shift Promo Mix to Fixed (High ROI)</b>
Fixed promos deliver <Value data={promo_stats} column=fixed_roi fmt=0.0/>× ROI vs <Value data={promo_stats} column=pct_roi fmt=0.0/>× for percentage. Test expanding fixed-discount campaigns for high-margin categories.
<br/><i>Owner:</i> Marketing. <i>Timeline:</i> 30 days to test, 60 days to scale.
</Alert>

<Alert status="positive">
<b>4. Cut Inventory to 90 Days (Capital Release)</b>
<Value data={inventory_kpis} column=avg_days_supply fmt=0/> days of supply is unsustainable. Target 90 days — industry standard — to free working capital for marketing and product development.
<br/><i>Owner:</i> Operations + Merchandising. <i>Timeline:</i> 90 days.
</Alert>

<Alert status="positive">
<b>5. Attack Controllable Returns (Margin Protection)</b>
<Value data={top_return_reason} column=reason/> is the top return reason. Fix supplier QC and sizing guides. Every 1% reduction in return rate flows straight to gross profit.
<br/><i>Owner:</i> Product + Sourcing. <i>Timeline:</i> 60 days.
</Alert>

<Alert status="positive">
<b>6. Fix Tablet UX (Hidden Conversion Drain)</b>
Tablet conversion lags mobile by roughly two-thirds. Audit tablet checkout flow, image sizing, and touch targets. This is a quick win with zero ad spend.
<br/><i>Owner:</i> Product + Engineering. <i>Timeline:</i> 30 days.
</Alert>

## Trend Detail

<LineChart
    data={revenue_trend}
    x=sales_date
    y=gross_margin_rate
    title="Gross Margin Rate Over Time"
    subtitle="Margin volatility signals pricing power erosion"
    yAxisTitle="Margin Rate"
    yFmt="pct2"
>
    <ReferenceLine y=0.15 label="15% Target" hideValue=true color=positive/>
</LineChart>

<DataTable data={revenue_trend} rows=10>
    <Column id=sales_date title="Date"/>
    <Column id=revenue title="Revenue" fmt=num0/>
    <Column id=gross_profit title="Gross Profit" fmt=num0/>
    <Column id=gross_margin_rate title="Margin" fmt=pct2/>
    <Column id=session_to_order_rate title="Conversion" fmt=pct2/>
    <Column id=order_count title="Orders" fmt=0/>
</DataTable>

## Related Stories

- [The 2019 Cliff](/01-stories/the-2019-cliff)
- [The Demand Capture Crisis](/01-stories/marketing/01-demand-capture-crisis)
- [The Retention Trap](/01-stories/customer/01-retention-trap)
- [The Inventory Capital Trap](/01-stories/product/01-inventory-capital-trap)
- [The Promo Paradox](/01-stories/marketing/02-promo-paradox)
- [The Revenue Anatomy](/01-stories/finance/01-revenue-anatomy)
