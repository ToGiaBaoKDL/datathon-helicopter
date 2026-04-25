---
title: Analytical Questions & Findings
---

# Analytical Questions & Findings

## Quick Stats

```sql summary_metrics
select
    avg(session_to_order_rate) as current_conversion,
    avg(return_record_rate) as current_return_rate,
    avg(gross_margin_rate) as current_margin
from datathon_warehouse.mart_daily_executive_kpis
where sales_date >= (select max(sales_date) - interval '90 days' from datathon_warehouse.mart_daily_executive_kpis)
```

<Grid cols=3>
    <BigValue
        data={summary_metrics}
        value=current_conversion
        title="Current Conversion"
        fmt="0.00%"
    />
    <BigValue
        data={summary_metrics}
        value=current_return_rate
        title="Current Return Rate"
        fmt="0.0%"
    />
    <BigValue
        data={summary_metrics}
        value=current_margin
        title="Current Margin"
        fmt="0.0%"
    />
</Grid>

---

## Executive / Commercial

### Q1: What is the true driver of the 2019 revenue collapse?

**Belongs to**: Executive KPI Pulse, Executive Summary

**Source**: `mart_daily_executive_kpis.session_to_order_rate`, `mart_daily_executive_kpis.sessions`

<Alert>
<b>Answered</b>
</Alert>

<b>Finding</b>: Conversion rate collapsed from 1.13% (2013) to 0.33% (2022), a 71% decline. Sessions remained flat at ~1,600 per day. The driver is <b>demand capture failure</b>, not demand generation failure.

<b>Critical inflection</b>: 2019 was the watershed year. Revenue dropped 38.6% (5.07M to 3.11M) and conversion dropped 40.2% (0.72% to 0.43%) in a single year. Something structural broke in 2019.

<b>Action</b>: Audit checkout flow, page load speed, mobile UX, and payment coverage. A +1pp conversion uplift projects ~150% incremental revenue.

```sql q1_conversion_trend
select
    date_part('year', sales_date) as year,
    avg(session_to_order_rate) as conversion_rate,
    avg(sessions)/1000 as sessions_k
from datathon_warehouse.mart_daily_executive_kpis
where sessions > 0
group by 1
order by 1
```

<BarChart
    data={q1_conversion_trend}
    x=year
    y=conversion_rate
    title="Conversion Rate Decline by Year"
    subtitle="The dominant driver of revenue pressure"
    yAxisTitle="Conversion Rate"
    yFmt="0.00%"
>
    <ReferenceLine y=1.0 label="1% Benchmark" hideValue=true color=info/>
</BarChart>

### Q2: Why did conversion stabilize at 0.31-0.33% in 2020-2022?

**Belongs to**: Executive KPI Pulse

**Source**: `mart_daily_executive_kpis.session_to_order_rate`

<Alert>
<b>Open</b>
</Alert>

<b>Hypothesis</b>: After the 2019 collapse (0.72% to 0.43%), conversion stabilized at a new floor of ~0.32%. This could mean:
- The business hit a structural floor (mobile UX limitations, payment coverage gaps)
- A competitor entered the market in 2019 and captured marginal buyers
- Platform migration or algorithm change degraded checkout flow

<b>Next Step</b>: Interview operations team about 2019 changes. Check for platform migrations, payment provider switches, or major competitor launches.

### Q3: Is the low bounce rate (0.4%) real or a measurement issue?

**Belongs to**: Inventory and Growth Scorecard

**Source**: `mart_daily_marketing_kpis.bounce_rate`

<Alert>
<b>Open</b>
</Alert>

<b>Hypothesis</b>: Typical e-commerce bounce rate is 20-50%. The 0.4% figure suggests either exceptional engagement or incorrect tracking (auto-refresh, single-page app behavior counted as multiple pages).

<b>Next Step</b>: Verify bounce rate definition with data engineering.

### Q4: Why does Wednesday outperform Saturday for conversion?

**Belongs to**: Executive KPI Pulse, Revenue and Drivers

**Source**: `mart_daily_executive_kpis.session_to_order_rate` by `extract(dow from sales_date)`

<Alert>
<b>Answered</b>
</Alert>

<b>Finding</b>: Wednesday conversion = 0.78%, Saturday = 0.67%. Wednesday revenue = 4.70M, Saturday = 3.91M.

<b>Interpretation</b>: Salary-cycle effect. Weekend browsing is leisure, weekday browsing is intent-driven.

<b>Action</b>: Shift promotional email sends to Tuesday-Wednesday. Reduce weekend ad spend.

### Q4b: Why does Q4 revenue underperform Q1?

**Belongs to**: Executive KPI Pulse, Revenue and Drivers

**Source**: `mart_daily_executive_kpis.revenue` by quarter

<Alert>
<b>Answered</b>
</Alert>

<b>Finding</b>: In every year from 2013 to 2022, Q4 revenue is <b>lower</b> than Q1. The Q4/Q1 ratio ranges from 0.61x (2018) to 0.89x (2015). Average: 0.76x.

<b>Interpretation</b>: This is counter-intuitive for e-commerce, where Q4 (holiday season) typically dominates. Two hypotheses:
- The business sells non-gift categories (e.g., activewear, outdoor) where demand peaks in Q1 (New Year fitness resolutions, outdoor season prep)
- Q4 discounts are deeper, eroding net revenue despite higher gross volume

<b>Action</b>: Reallocate Q4 marketing budget to Q1. Test "New Year, New You" campaigns in January instead of Black Friday clones in November.

```sql q4b_quarterly_revenue
select
    date_part('year', sales_date) as year,
    avg(case when date_part('quarter', sales_date) = 1 then revenue end)/1e6 as q1_rev,
    avg(case when date_part('quarter', sales_date) = 4 then revenue end)/1e6 as q4_rev
from datathon_warehouse.mart_daily_executive_kpis
group by 1
order by 1
```

<BarChart
    data={q4b_quarterly_revenue}
    x=year
    y=q1_rev
    y2=q4_rev
    y2SeriesType=line
    title="Q1 vs Q4 Average Daily Revenue"
    subtitle="Bar = Q1, Line = Q4 — Q1 consistently outperforms"
    yAxisTitle="Revenue"
    y2AxisTitle="Revenue"
    yFmt="num0"
    y2Fmt="num0"
/>

### Q5: What is the revenue per visitor trend?

**Belongs to**: Executive Summary

**Source**: `mart_daily_executive_kpis.revenue / mart_daily_executive_kpis.sessions`

<Alert>
<b>Answered</b>
</Alert>

<b>Finding</b>: Revenue per session collapsed from 250 VND (2016) to 95-106 VND (2020-2022), a 60% drop. However, AOV <b>increased</b> from 25,589 to 32,489 VND (+27%).

<b>Interpretation</b>: Volume vs value trade-off. Fewer orders but higher ticket size. The conversion drop (-71%) outweighs the AOV gain (+27%), so total revenue still fell 50%.

<b>Action</b>: The AOV increase is a bright spot. Double down on bundling and cross-sell, but only after fixing the conversion leak.

```sql q5_rev_per_visitor
select
    date_part('year', sales_date) as year,
    sum(revenue)::double / sum(sessions) as revenue_per_session,
    sum(revenue)::double / sum(order_count) as aov
from datathon_warehouse.mart_daily_executive_kpis
where sessions > 0
group by 1
order by 1
```

<LineChart
    data={q5_rev_per_visitor}
    x=year
    y=revenue_per_session
    y2=aov
    y2SeriesType=line
    title="Revenue per Session vs AOV by Year"
    subtitle="Bar = revenue per session, Line = AOV"
    yAxisTitle="Revenue per Session"
    y2AxisTitle="AOV"
    yFmt="num0"
    y2Fmt="num0"
/>

---

## Operations / Fulfillment

### Q6: Does late delivery cause higher return rates?

**Belongs to**: Fulfillment and Returns

**Source**: `mart_daily_executive_kpis.avg_days_to_deliver`, `mart_daily_returns_kpis.return_record_rate`

<Alert>
<b>Answered</b>
</Alert>

<b>Finding</b>: Correlation = 0.024 (negligible). Days with delivery greater than 7 days show 0% return rate (low order volume, not causal).

<b>Interpretation</b>: Delivery speed is NOT a major return driver. Product quality and sizing are bigger factors.

### Q7: Why is free shipping usage only 0.14% when average fee is 5 VND?

**Belongs to**: Fulfillment and Returns

**Source**: `mart_daily_fulfillment_kpis.free_shipping_share`, `mart_daily_fulfillment_kpis.avg_shipping_fee`

<Alert>
<b>Answered</b>
</Alert>

<b>Finding</b>: Shipping fee is effectively zero (5 VND), yet only 0.14% of orders use free shipping promotions.

<b>Action</b>: Test "free shipping on all orders" messaging. The cost is already near zero; the psychological barrier is what matters.

### Q8: What is the relationship between stockouts and cancellations?

**Belongs to**: Revenue and Drivers

**Source**: `mart_forecast_daily_base.cancelled_line_count`, `mart_daily_executive_kpis.avg_stockout_days`

<Alert>
<b>Answered</b>
</Alert>

<b>Finding</b>: Correlation = 0.024 (negligible). Cancellations (~10%) are NOT driven by stockouts.

<b>Interpretation</b>: Cancellations are likely due to pricing errors, promo code issues, or buyer remorse.

<b>Next Step</b>: Correlate cancellation spikes with promo campaigns or pricing changes.

### Q9: Do promotional periods show post-promo dip?

**Belongs to**: Promotion Effectiveness

**Source**: `mart_promotion_effectiveness`, `mart_forecast_daily_base.revenue`

<Alert>
<b>Open</b>
</Alert>

<b>Hypothesis</b>: If promotions pull forward demand rather than create new demand, revenue should dip below baseline in the weeks after a campaign ends.

<b>Next Step</b>: Compare revenue in weeks after major promos vs same weeks in non-promo periods.

---

## Product / Category

### Q10: Which product segment is most profitable?

**Belongs to**: Category and Region Performance

**Source**: `mart_monthly_category_performance.gross_margin_rate` by `segment`

<Alert>
<b>Answered</b>
</Alert>

<b>Finding</b>: Activewear = 17.7% margin, Performance = 11.7% margin (6pp gap). Trendy = 19.1% margin but small scale (0.3B).

<b>Critical finding</b>: Performance segment margin is <b>volatile</b> (6.7% in 2019, 13.2% in 2020, 12.6% in 2022), not a structural collapse. Revenue, however, fell from 316M (2018) to 136M (2022).

<b>Activewear paradox</b>: Activewear has the highest margin (17-22%) but revenue is shrinking steadily from 304M (2014) to 78M (2022). The business is losing share in its most profitable segment.

<b>Action</b>: Investigate why Activewear revenue is declining despite strong margin. Competitor entry? Assortment narrowing? Marketing underinvestment?

```sql q10_segment_margin
select
    segment,
    sum(gross_revenue)/1e9 as revenue_b,
    sum(gross_profit)/sum(gross_revenue) as margin_rate,
    avg(return_unit_rate) as return_rate
from datathon_warehouse.mart_monthly_category_performance
group by 1
order by margin_rate desc
```

<BarChart
    data={q10_segment_margin}
    x=segment
    y=margin_rate
    y2=return_rate
    y2SeriesType=line
    title="Margin Rate and Return Rate by Segment"
    subtitle="Bar = margin rate, Line = return rate"
    yAxisTitle="Margin Rate"
    y2AxisTitle="Return Rate"
    yFmt="0.0%"
    y2Fmt="0.0%"
>
    <ReferenceLine y=0.15 label="15% Target" hideValue=true color=positive/>
</BarChart>

### Q11: Do certain colors or sizes have higher return rates?

**Belongs to**: Product Lifecycle and Health

**Source**: `mart_product_lifetime_performance.return_unit_rate` by `color`, `size`

<Alert>
<b>Answered</b>
</Alert>

<b>Finding</b>: White = 4.2% return (highest), Black = 3.0% (lowest). Size variation is minimal (S/L = 3.6% vs M/XL = 3.4%).

<b>Interpretation</b>: White products may have quality issues (see-through fabric, staining) or sizing inconsistencies.

<b>Action</b>: Inspect white product supplier QC. Add fabric weight and thickness to product descriptions.

### Q12: Which categories contain the 359 negative-margin products?

**Belongs to**: Product Lifecycle and Health

**Source**: `mart_product_lifetime_performance.realized_margin_rate` by `category`, `segment`

<Alert>
<b>Answered</b>
</Alert>

<b>Finding</b>: Streetwear/Everyday = 87 products, Outdoor/Activewear = 85 products, Streetwear/Performance = 59 products. These 3 segments account for 64% of all negative-margin SKUs.

<b>Impact</b>: These products destroy value on every sale.

<b>Action</b>: Run clearance to liquidate, then delist. Do not restock unless pricing is corrected.

### Q13: Are returns concentrated in specific suppliers or batches?

**Belongs to**: Product Lifecycle and Health

**Source**: Requires `supplier_id` or `batch_id` (not currently in marts)

<Alert>
<b>Open</b>
</Alert>

<b>Hypothesis</b>: The 5.5% return rate may be driven by a small number of bad suppliers. If 20% of suppliers cause 80% of returns, targeted QC would be more efficient than broad inspection.

<b>Next Step</b>: Requires supplier_id and batch_id in raw data.

---

## Customer / Retention

### Q14: Why is month-1 retention only ~3.5%?

**Belongs to**: Customer Cohort and RFM

**Source**: `mart_monthly_customer_cohort.retention_rate` where `months_since_first_order = 1`

<Alert>
<b>Answered</b>
</Alert>

<b>Finding</b>: 22,358 customers (25%) never placed a second order. Retention drops to ~3.5% by month 1.

<b>Hidden insight</b>: After month 1, retention is remarkably stable: M3 = 3.35%, M6 = 3.23%, M12 = 3.41%. Customers who survive month 1 are essentially retained for life.

<b>Action</b>: The entire retention problem is the <b>first 30 days</b>. Send a time-limited second-purchase incentive within 30 days of first order.

### Q15: Which acquisition channel has the best retention?

**Belongs to**: Customer Cohort and RFM

**Source**: `mart_cohort_by_channel_age.retention_rate` by `acquisition_channel`

<Alert>
<b>Answered</b>
</Alert>

<b>Finding</b>: Direct channel = 12.4% month-1 retention, Organic Search = 6.5% (2x difference).

<b>Interpretation</b>: Intent quality matters. Direct visitors are brand-seekers; organic search visitors are browsers.

<b>Action</b>: Shift budget toward direct and referral. Tighten paid search keyword targeting to high-intent terms.

```sql q15_channel_retention
select
    acquisition_channel,
    avg(case when months_since_first_order = 1 then retention_rate end) as month1_retention
from datathon_warehouse.mart_cohort_by_channel_age
group by 1
order by month1_retention desc
```

<BarChart
    data={q15_channel_retention}
    x=acquisition_channel
    y=month1_retention
    title="Month-1 Retention by Acquisition Channel"
    subtitle="Direct and referral customers are twice as loyal"
    yAxisTitle="Retention Rate"
    yFmt="0.0%"
>
    <ReferenceLine y=0.20 label="20% Benchmark" hideValue=true color=positive/>
</BarChart>

### Q16: Do older customers have higher retention?

**Belongs to**: Customer Cohort and RFM

**Source**: `mart_cohort_by_channel_age.retention_rate` by `age_group`

<Alert>
<b>Answered</b>
</Alert>

<b>Finding</b>: 55+ age group = 11.5% month-1 retention, 25-34 = 7.5% (weakest).

<b>Interpretation</b>: Older customers are more loyal but represent a smaller segment.

<b>Action</b>: Improve 25-34 retention (largest segment) with mobile-first UX and social proof.

### Q17: Are we acquiring customers profitably?

**Belongs to**: Customer Cohort and RFM

**Source**: `mart_customer_rfm.total_revenue`, `mart_customer_rfm.total_orders` by `acquisition_channel`

<Alert>
<b>Answered (partial)</b>
</Alert>

<b>Finding</b>: LTV is nearly identical across channels (~180K VND). AOV is also flat (~25K VND). Channel affects <b>retention velocity</b>, not basket size.

<b>Hypothesis</b>: Direct customers reach the same LTV faster. If CAC is similar across channels, Direct has the shortest payback period.

<b>Next Step</b>: Calculate payback period by channel. Requires CAC data from marketing spend.

### Q27: How concentrated is revenue among top customers?

**Belongs to**: Customer Cohort and RFM, Executive Summary

**Source**: `mart_customer_rfm.total_revenue`

<Alert>
<b>Answered</b>
</Alert>

<b>Finding</b>: Top 10% of customers (Decile 10) generate <b>40.0%</b> of total revenue. Top 20% generate <b>60.7%</b>. Bottom 10% generate only 0.4%.

<b>Interpretation</b>: This is a hyper-Pareto distribution. The business is extremely dependent on a small number of high-value customers.

<b>Risk</b>: Losing even 1% of top-decile customers = ~1.5% revenue loss.

<b>Action</b>: Implement VIP program for top decile. Personalized service, early access to new products, dedicated support.

### Q28: Why does gross margin swing wildly year to year?

**Belongs to**: Executive Summary, Revenue and Drivers

**Source**: `mart_daily_executive_kpis.gross_margin_rate`, `mart_daily_executive_kpis.total_discount_amount`

<Alert>
<b>Open</b>
</Alert>

<b>Finding</b>: Margin ranges from 7.9% (2021) to 20.7% (2012). Discount share of revenue is stable (~4.5-5.3%), so discounts do not explain the volatility.

<b>Hypothesis</b>: Margin swings are driven by <b>mix effects</b> — years with higher Performance segment share have lower overall margin. 2012 had high margin (20.7%) but low scale; 2021 had low margin (7.9%) despite stable operations.

<b>Next Step</b>: Decompose yearly margin into price effect, cost effect, and mix effect.

### Q29: Why does Streetwear have so many discontinued products?

**Belongs to**: Product Lifecycle and Health, Category and Region Performance

**Source**: `mart_product_lifetime_performance.lifecycle_stage` by `category`

<Alert>
<b>Answered</b>
</Alert>

<b>Finding</b>: Streetwear = 296 active, 510 discontinued, 443 never_sold. Active products are only 23% of the Streetwear portfolio.

<b>Interpretation</b>: Streetwear has the most "churn" in the portfolio — products are launched, sold briefly, then discontinued. This suggests fast-fashion dynamics: short product lifecycles, trend-driven demand.

<b>Action</b>: Reduce initial order quantities for Streetwear. Use pre-orders or small-batch drops to test demand before committing to inventory. The current model creates 63% dead stock.

---

## Marketing / Promotions

### Q18: Why do fixed-discount promos have 11x higher ROI than percentage?

**Belongs to**: Promotion Effectiveness

**Source**: `mart_promotion_effectiveness.total_net_revenue / mart_promotion_effectiveness.total_discount_amount`

<Alert>
<b>Answered</b>
</Alert>

<b>Finding</b>: Fixed = 82x ROI, 1.2% discount rate. Percentage = 7.2x ROI, 12.9% discount rate.

<b>Interpretation</b>: Fixed discounts preserve margin better. Percentage discounts erode margin on high-AOV orders.

<b>Action</b>: Test expanding fixed-discount campaigns for high-margin categories.

```sql q18_promo_roi
select
    promo_type,
    count(*) as campaigns,
    sum(total_net_revenue)/1e9 as revenue_b,
    sum(total_net_revenue) / nullif(sum(total_discount_amount), 0) as roi,
    avg(discount_rate) as avg_discount
from datathon_warehouse.mart_promotion_effectiveness
where total_orders > 0
group by 1
order by roi desc
```

<BarChart
    data={q18_promo_roi}
    x=promo_type
    y=roi
    title="ROI by Promotion Type"
    subtitle="Fixed discounts deliver 11x higher ROI"
    yAxisTitle="ROI (Revenue per Discount VND)"
    yFmt="0.0x"
/>

### Q19: Are stackable promotions more or less efficient?

**Belongs to**: Promotion Effectiveness

**Source**: `mart_promotion_effectiveness.stackable_flag`

<Alert>
<b>Open</b>
</Alert>

<b>Hypothesis</b>: Stackable promos may drive volume but destroy margin through compound discounting.

<b>Next Step</b>: Compare ROI of stackable (12 campaigns, avg discount 12.0%) vs non-stackable (38 campaigns, avg discount 11.7%).

### Q20: Do category-specific promos outperform site-wide?

**Belongs to**: Promotion Effectiveness

**Source**: `mart_promotion_effectiveness.avg_order_value` by `applicable_category`

<Alert>
<b>Answered</b>
</Alert>

<b>Finding</b>: Streetwear promos AOV = 18,695 vs Outdoor = 13,125. Category promos attract higher-intent buyers.

<b>Action</b>: Test more category-specific campaigns instead of defaulting to site-wide percentage discounts.

### Q25: Do promotions cannibalize non-promo revenue?

**Belongs to**: Promotion Effectiveness, Revenue and Drivers

**Source**: `mart_forecast_daily_base.revenue`, `mart_forecast_daily_base.total_discount_amount`

<Alert>
<b>Answered</b>
</Alert>

<b>Finding</b>: Promo days (discount greater than 1M VND) generate 8.76M revenue vs 4.13M on non-promo days — a 2.1x lift. However, AOV on promo days is <b>lower</b> (21,349 vs 25,767 VND).

<b>Interpretation</b>: Promotions drive volume but erode AOV. The 2.1x revenue lift may be pulling forward demand rather than creating incremental demand.

<b>Action</b>: Track revenue in the 2 weeks after each major promo. If post-promo revenue dips below baseline, campaigns are cannibalizing future sales.

### Q26: Do deeper discounts drive higher conversion?

**Belongs to**: Promotion Effectiveness, Executive KPI Pulse

**Source**: `mart_forecast_daily_base.total_discount_amount / revenue`, `mart_daily_executive_kpis.session_to_order_rate`

<Alert>
<b>Answered</b>
</Alert>

<b>Finding</b>: Deep discount days (greater than 15% of revenue) have the highest conversion (0.86%), followed by moderate (5-15%) at 0.75%, and light discount (less than 5%) at 0.70%.

<b>Interpretation</b>: Discount depth and conversion are positively correlated. However, deep discount days also have the lowest absolute revenue (3.24M vs 4.46M) because they are infrequent and may signal distress selling.

<b>Action</b>: Test moderate discounts (5-15%) as the sweet spot — better conversion than light discounts without the margin destruction of deep discounts.

---

## Inventory / Supply Chain

### Q21: Why is days of supply 930 days (~2.5 years)?

**Belongs to**: Inventory and Growth Scorecard

**Source**: `mart_monthly_inventory_snapshot.avg_days_of_supply`

<Alert>
<b>Answered</b>
</Alert>

<b>Finding</b>: 930 days of supply with 15.2% sell-through rate. Fill rate is healthy (96.1%).

<b>Interpretation</b>: Massive overstock. Working capital is severely tied up in slow-moving inventory.

<b>Action</b>: Target 90 days of supply (industry standard). Liquidate dormant and discontinued stock.

### Q22: Why do 30,495 product-months have both stockout and overstock flags?

**Belongs to**: Inventory and Growth Scorecard

**Source**: Raw inventory data

<Alert>
<b>Open</b>
</Alert>

<b>Hypothesis</b>: Data quality issue in raw inventory classification, or products have size/color variants where some are stocked out and others overstocked.

<b>Next Step</b>: Verify flag logic with data engineering.

---

## Methodology / Data Quality

### Q23: Is the revenue trend slope meaningful?

**Belongs to**: Revenue and Drivers

**Source**: `mart_daily_executive_kpis.revenue` trend regression

<Alert>
<b>Answered</b>
</Alert>

<b>Finding</b>: Slope = -702 VND/day, R2 = 8.8%. Linear model is misleading.

<b>Truth</b>: Revenue rose to 2016 peak (5.75M/day) then collapsed 50% to ~2.9M/day. This is a <b>structural break</b>, not a linear trend.

<b>Implication</b>: Do not use linear trend for forecasting. Use regime-switching models or segment by pre/post-2018.

### Q24: Are return rates grouped by return_date or order_date?

**Belongs to**: Fulfillment and Returns

**Source**: `int_daily_commercial_signals`, `mart_monthly_category_performance`, `mart_monthly_product_health`

<Alert>
<b>Answered</b>
</Alert>

<b>Finding</b>: 3 models previously grouped by return_date, causing rates greater than 1 (e.g., 1.11 on 2013-03-02).

<b>Fix</b>: Changed to order_date cohort. Max rate now 0.17 (17%).

---

## Open Questions Backlog

```sql open_backlog
select
    'High' as priority,
    'Why did Performance segment margin collapse 2019?' as question,
    'Product' as domain,
    'Margin recovery (+6pp)' as estimated_impact
union all
select 'High', 'Is bounce rate measurement correct?', 'Marketing', 'Conversion insight'
union all
select 'High', 'Why did conversion stabilize at 0.32% floor?', 'Executive', 'Conversion recovery'
union all
select 'Medium', 'Do stackable promos destroy margin?', 'Marketing', 'Promo optimization'
union all
select 'Medium', 'What drives 10% cancellation rate?', 'Operations', 'Revenue recovery (+10%)'
union all
select 'Medium', 'Why white products have higher returns?', 'Product', 'Quality improvement'
union all
select 'Medium', 'Do promotional periods show post-promo dip?', 'Marketing', 'Demand forecasting'
union all
select 'Medium', 'Are we acquiring customers profitably?', 'Customer', 'CAC/LTV optimization'
union all
select 'High', 'Why does gross margin swing 7.9% to 20.7% yearly?', 'Executive', 'Margin stability'
union all
select 'Medium', 'Do VIP programs reduce top-decile churn?', 'Customer', 'Revenue protection'
union all
select 'Low', 'Are returns concentrated by supplier?', 'Product', 'Targeted QC'
union all
select 'Low', 'Payment method impact on conversion?', 'Marketing', 'Checkout optimization'
```

<DataTable data={open_backlog} rows=10/>
