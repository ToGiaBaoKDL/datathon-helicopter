# Evidence Pages Enhancement Plan

## Context

- **Stack**: Evidence.dev + DuckDB v1.5.2 + dbt
- **Current pages**: 12 pages across 6 business domains (executive, finance, operations, marketing, customer, product)
- **Evidence components available**: BigValue, Delta, Alert, ReferenceLine, ReferenceArea, BarChart, LineChart, AreaChart, ScatterPlot, Heatmap, CalendarHeatmap, DataTable, Tabs, Details, Grid, Slider
- **DuckDB stats**: `corr()`, `regr_slope()`, `regr_r2()`, `quantile()`, `stddev_samp()`, `covar_samp()` available.

---

## A. Tăng chiều sâu phân tích business

### A1. Cohort retention theo acquisition channel và age group

**Problem**: `mart_monthly_customer_cohort` grain = (cohort_month, months_since_first_order). Không có channel/age dimensions.

**Solution**: Create new dbt model `mart_cohort_retention_by_channel_age.sql`:
- Join `mart_monthly_customer_cohort` với `mart_customer_rfm` qua customer_id → lấy acquisition_channel, age_group
- Grain mới: (cohort_month, months_since_first_order, acquisition_channel, age_group)
- Region không có trong customer marts → skip (không đủ data)

**Evidence page updates** (`customer-cohort-and-rfm.md`):
- **Heatmap**: retention_rate × months_since_first_order × acquisition_channel
- **LineChart**: retention curves grouped by channel (series=acquisition_channel)
- **LineChart**: retention curves grouped by age_group (series=age_group)
- **BigValue**: best-performing channel (highest month-6 retention)
- **BarChart**: cohort_size by channel × cohort_month

**New SQL patterns**:
```sql
select
    acquisition_channel,
    months_since_first_order,
    avg(retention_rate) as avg_retention
from mart_cohort_retention_by_channel_age
group by 1, 2
```

### A2. RFM segmentation — thêm CLV tier và churn risk segment

**Problem**: Page hiện tại chỉ có raw RFM metrics, chưa segment hóa.

**Solution**: Tính segments inline trong Evidence SQL (không cần new mart):
- **CLV tier**: `ntile(4) over (order by total_revenue)` → Platinum, Gold, Silver, Bronze
- **Churn risk**: So sánh recency_days với 2× avg_days_between_orders
  - `recency_days <= avg_gap` → Active
  - `recency_days <= 2× avg_gap` → At Risk
  - `recency_days > 2× avg_gap` → Churned
- **RFM combined score**: Recency quintile × Frequency quintile × Monetary quintile

**Evidence page updates**:
- **BigValue**: count by CLV tier (4 BigValues in a row)
- **BigValue**: count by churn risk (3 BigValues)
- **BarChart**: avg_order_value by CLV tier
- **BarChart**: customer count by churn risk × acquisition_channel
- **DataTable**: top 10 churn-risk customers with revenue and recency
- **ScatterPlot**: recency_days vs total_revenue, color=churn_risk, size=total_orders

**New components**: Delta để so sánh segment performance:
```markdown
Platinum customers generate <Value data={clv_stats} column=platinum_pct/> of total revenue.
```

### A3. Promotion deep-dive — A/B test giả định + category impact

**Problem**: Page hiện chỉ có summary metrics, chưa có causal analysis.

**Solution**:
- **A/B test giả định** (percentage vs fixed discount):
  - T-test qua SQL: `avg(total_net_revenue)`, `stddev_samp(total_net_revenue)` by promo_type
  - Effect size: Cohen's d = (mean_pct - mean_fixed) / pooled_stddev
  - Evidence: BigValue hiển thị effect size, Alert nếu p < 0.05
  - Note: "Giả định" vì không phải randomized A/B test thực sự

- **Category impact analysis** (thay thế cannibalization phức tạp):
  - New mart `mart_promotion_category_impact.sql`: so sánh revenue by category
    - Trong promo period (start_date → end_date) vs baseline (same duration trước promo)
  - Grain: (promo_id, applicable_category)
  - Metrics: promo_revenue, baseline_revenue, lift_pct, halo_or_cannibal_flag

**Evidence page updates** (`promotion-effectiveness.md`):
- **BarChart**: avg revenue per campaign by promo_type (with stddev error bands qua SQL)
- **ScatterPlot**: discount_rate vs revenue lift (lift = vs category baseline)
- **Alert**: Warning nếu effect size nhỏ hoặc không significant
- **DataTable**: campaigns ranked by ROI (revenue / discount_amount)
- **Tabs**: Tab 1 = Overview, Tab 2 = A/B Analysis, Tab 3 = Category Impact

---

## C. Tăng storytelling cho Evidence

### C1. Narrative text giữa các chart

**Pattern**: Mỗi section có structure:
```markdown
## Section Title

<Alert status="info">
Insight: Conversion rate on weekends is 23% higher than weekdays.
</Alert>

<Alert status="positive">
Action: Consider increasing weekend ad spend by 15%.
</Alert>

<BarChart ... />

> *Detail*: This pattern has been consistent since 2020, suggesting a structural 
> shift in customer shopping behavior rather than a temporary trend.
```

**Apply to all pages**:
- `executive-kpi-pulse.md`: Add narrative after each chart explaining "so what"
- `revenue-and-drivers.md`: Add causal interpretation between traffic and revenue
- `customer-cohort-and-rfm.md`: Add retention insights with actionable recommendations

### C2. Anomaly highlight

**Evidence components**: `ReferenceArea`, `ReferenceLine`

**Implementation**:
- Compute anomaly threshold in SQL (mean ± 2σ)
- Use `ReferenceArea` to highlight anomalous periods
- Add `Alert` component when current period is anomalous

**Example** (add to `executive-kpi-pulse.md`):
```sql
select
    sales_date,
    revenue,
    avg(revenue) over () + 2 * stddev_samp(revenue) over () as upper,
    avg(revenue) over () - 2 * stddev_samp(revenue) over () as lower
from mart_daily_executive_kpis
```

```markdown
<AreaChart ...>
    <ReferenceArea xMin='2023-01-15' xMax='2023-01-20' label='Tet Spike'/>
</AreaChart>
```

### C3. What-if scenario

**Example**: "Nếu conversion rate tăng 1% thì revenue tăng bao nhiêu?"

**SQL**:
```sql
select
    avg(sessions) * 0.01 * avg(revenue / sessions) as incremental_revenue,
    avg(revenue) as baseline_revenue,
    incremental_revenue / baseline_revenue as pct_lift
from mart_forecast_daily_base
where sales_date >= '2023-01-01'
```

**Evidence components**:
- **BigValue**: Baseline revenue
- **BigValue**: Incremental revenue (what-if)
- **Delta**: % lift
- **Slider**: `conversion_lift` input → recalculate dynamically

**Apply to**:
- `executive-kpi-pulse.md`: Conversion rate what-if
- `marketing/promotion-effectiveness.md`: Discount depth what-if
- `operations/inventory-and-growth-scorecard.md`: Stockout reduction what-if

---

## D. Executive summary page

**New page**: `executive/executive-summary.md`

**Structure**:

### Top 5 Insights (auto-computed from other marts)

1. **Revenue trend**: Direction + slope + significance (from `regr_slope` + `regr_r2`)
2. **Best performing segment**: Channel/age_group/category with highest growth
3. **Customer health**: % at-risk customers + CLV distribution shift
4. **Operational risk**: Stockout days trend + fulfillment SLA
5. **Promotion ROI**: Best campaign type + category impact warning

### Top 5 Risks (from `mart_daily_risk_flags`)

1. **Stockout risk days** (flag count)
2. **Return spike days** (flag count)
3. **Conversion drop days** (flag count)
4. **Revenue decline streak** (consecutive days below mean)
5. **Margin compression** (gross_margin_rate trend)

### Recommended Actions

Static markdown with dynamic values inserted:
```markdown
- **Focus on {best_channel}**: This channel drives {best_channel_pct} of revenue 
  with {best_channel_margin} margin.
- **Address inventory risk**: {stockout_flag_count} days had stockout risk in the 
  last 30 days.
- **Re-engage at-risk customers**: {at_risk_count} customers ({at_risk_pct}) 
  haven't ordered in 2× their normal gap.
```

**Components**:
- **Grid**: 3 columns (Insights | Risks | Actions)
- **BigValue**: 5 KPIs in header row
- **DataTable**: Risk flags detail
- **Alert**: Critical issues in red

---

## Implementation Priority

### Phase 1 (High impact, low effort)
1. Add narrative text + Alert components to existing pages
2. RFM segmentation (CLV tier, churn risk) — SQL only
3. What-if scenarios with BigValue + Delta
4. Executive summary page

### Phase 2 (Medium effort)
5. Cohort retention by channel/age — new dbt mart `mart_cohort_retention_by_channel_age`
6. Anomaly highlight with ReferenceArea on key charts
7. Promotion category impact — new dbt mart `mart_promotion_category_impact`

---

## Files to Create / Modify

### New dbt models
- `dbt/models/marts/customer/mart_cohort_retention_by_channel_age.sql`
- `dbt/models/marts/marketing/mart_promotion_category_impact.sql`

### New Evidence pages
- `reports/evidence/pages/eda/executive/executive-summary.md`

### Modify Evidence pages
- `reports/evidence/pages/eda/customer/customer-cohort-and-rfm.md`
- `reports/evidence/pages/eda/marketing/promotion-effectiveness.md`
- `reports/evidence/pages/eda/executive/executive-kpi-pulse.md`
- `reports/evidence/pages/eda/finance/revenue-and-drivers.md`
- `reports/evidence/pages/eda/operations/inventory-and-growth-scorecard.md`
- `reports/evidence/pages/index.md` (add link to executive-summary)

### Evidence components sử dụng
- `Alert`, `Delta`, `BigValue`, `Value`
- `ReferenceLine`, `ReferenceArea`
- `Tabs`, `Details`, `Grid`
- `BarChart`, `LineChart`, `AreaChart`, `ScatterPlot`, `Heatmap`
- `DataTable`, `Slider` (cho what-if)
