---
title: MCQ Answer Key
---

This page answers all 10 multiple-choice questions from Part 1 of the Datathon Round 1 exam.

```sql answer_key
select 'Q1' as question, 'Median inter-order gap' as topic, 'C' as choice, '144 days' as answer
union all select 'Q2', 'Highest-margin segment', 'D', 'Standard'
union all select 'Q3', 'Streetwear top return reason', 'B', 'wrong_size'
union all select 'Q4', 'Lowest-bounce traffic source', 'C', 'email_campaign'
union all select 'Q5', 'Promo coverage in order lines', 'C', '39%'
union all select 'Q6', 'Highest-loyalty age group', 'A', '55+'
union all select 'Q7', 'Revenue leader by region', 'C', 'East'
union all select 'Q8', 'Cancelled order payment method', 'A', 'credit_card'
union all select 'Q9', 'Highest-return product size', 'A', 'S'
union all select 'Q10', 'Highest-value installment plan', 'C', '6 installments'
```

## Answer Key

<DataTable data={answer_key} rows=10>
    <Column id=question title="Question"/>
    <Column id=topic title="Topic"/>
    <Column id=choice title="Choice"/>
    <Column id=answer title="Answer"/>
</DataTable>

---

```sql mcq_metrics
select *
from datathon_warehouse.mart_part1_mcq_metrics
order by metric_key
```

```sql q1
select metric_value as val from datathon_warehouse.mart_part1_mcq_metrics where metric_key = 'q1_median_inter_order_gap_days'
```

```sql q2
select metric_value as val from datathon_warehouse.mart_part1_mcq_metrics where metric_key = 'q2_top_segment_avg_margin'
```

```sql q3
select metric_value as val from datathon_warehouse.mart_part1_mcq_metrics where metric_key = 'q3_top_streetwear_return_reason_count'
```

```sql q4
select metric_value as val from datathon_warehouse.mart_part1_mcq_metrics where metric_key = 'q4_lowest_avg_bounce_rate'
```

```sql q5
select metric_value as val from datathon_warehouse.mart_part1_mcq_metrics where metric_key = 'q5_promo_line_percentage'
```

```sql q6
select metric_value as val from datathon_warehouse.mart_part1_mcq_metrics where metric_key = 'q6_top_age_group_avg_orders_per_customer'
```

```sql q7
select metric_value as val from datathon_warehouse.mart_part1_mcq_metrics where metric_key = 'q7_top_region_total_revenue'
```

```sql q8
select metric_value as val from datathon_warehouse.mart_part1_mcq_metrics where metric_key = 'q8_top_cancelled_payment_method_count'
```

```sql q9
select metric_value as val from datathon_warehouse.mart_part1_mcq_metrics where metric_key = 'q9_highest_return_rate_by_size'
```

```sql q10
select metric_value as val from datathon_warehouse.mart_part1_mcq_metrics where metric_key = 'q10_highest_avg_payment_value_by_installments'
```

## Q1. Median Inter-Order Gap

**Question:** Among customers with more than one order, what is the approximate median number of days between consecutive orders?

<Alert status="positive">
<b>Answer: C) 144 days</b>
</Alert>

<Alert status="info">
<b>Reason:</b> The median gap is <b><Value data={q1} column=val fmt=0/> days</b> — customers who do return typically come back after roughly 5 months. This long cycle reflects low purchase frequency in fashion e-commerce and justifies why retention campaigns should target 90–120 day windows rather than 30-day ones.
</Alert>

---

## Q2. Highest-Margin Product Segment

**Question:** Which product segment has the highest average gross margin rate, defined as (price − cogs) / price?

<Alert status="positive">
<b>Answer: D) Standard</b>
</Alert>

<Alert status="info">
<b>Reason:</b> Standard leads with <b><Value data={q2} column=val fmt=pct2/></b> average margin, outperforming Premium, Activewear, and Performance. This is counter-intuitive — basic products often have lower COGS relative to price than trend-driven SKUs with higher sourcing complexity.
</Alert>

---

## Q3. Top Return Reason for Streetwear

**Question:** For Streetwear products, which return reason appears most frequently?

<Alert status="positive">
<b>Answer: B) wrong_size</b>
</Alert>

<Alert status="info">
<b>Reason:</b> Wrong-size returns dominate Streetwear (<b><Value data={q3} column=val fmt=0/> cases</b>), far exceeding defective, changed_mind, and not_as_described. This signals a sizing-guide or fit-prediction problem specific to casual fashion — sizing inconsistency across suppliers is the likely root cause.
</Alert>

---

## Q4. Lowest-Bounce Traffic Source

**Question:** Which traffic source has the lowest average bounce rate across all days it appears?

<Alert status="positive">
<b>Answer: C) email_campaign</b>
</Alert>

<Alert status="info">
<b>Reason:</b> Email campaigns show the lowest bounce at <b><Value data={q4} column=val fmt=pct2/></b> — visitors arriving via email are pre-qualified (they opened and clicked), making them the highest-intent traffic segment. Paid search and social media have higher bounce because they capture broader, less-qualified audiences.
</Alert>

---

## Q5. Promo Coverage in Order Lines

**Question:** Approximately what percentage of order_item lines have a non-null promo_id?

<Alert status="positive">
<b>Answer: C) 39%</b>
</Alert>

<Alert status="info">
<b>Reason:</b> <b><Value data={q5} column=val fmt=pct2/></b> of all order lines carry a promotion. This is high — nearly 2 in 5 lines are discounted, suggesting the business runs a promotion-heavy model. The risk: margin erosion if discount depth is not tightly controlled relative to revenue lift.
</Alert>

---

## Q6. Highest-Loyalty Age Group

**Question:** Among customers with a known age_group, which group has the highest average number of orders per customer?

<Alert status="positive">
<b>Answer: A) 55+</b>
</Alert>

<Alert status="info">
<b>Reason:</b> The 55+ segment averages <b><Value data={q6} column=val fmt=0.0/> orders per customer</b>, the highest of any age group. Older customers buy less frequently but remain loyal longer. The 25–34 group is the largest by headcount but has lower per-customer order frequency — the retention opportunity lies in converting volume into loyalty.
</Alert>

---

## Q7. Revenue Leader by Region

**Question:** Which geographic region generates the highest total revenue?

<Alert status="positive">
<b>Answer: C) East</b>
</Alert>

<Alert status="info">
<b>Reason:</b> East generates <b><Value data={q7} column=val fmt=num0/> VND</b>, the highest of all regions. Despite East's volume leadership, its return rate and fulfillment costs must be monitored — high-revenue regions often mask quality or logistics friction at scale.
</Alert>

---

## Q8. Cancelled Order Payment Method

**Question:** Among cancelled orders, which payment method is used most frequently?

<Alert status="positive">
<b>Answer: A) credit_card</b>
</Alert>

<Alert status="info">
<b>Reason:</b> Credit card leads cancelled orders with <b><Value data={q8} column=val fmt=0/> cancelled orders</b>. This does not mean credit card is riskier — it simply reflects credit card's dominant share of total orders. The more relevant metric is cancellation <i>rate</i> by method, where COD typically shows higher relative cancellation.
</Alert>

---

## Q9. Highest-Return Product Size

**Question:** Among S, M, L, XL, which size has the highest return rate (returns / order_items)?

<Alert status="positive">
<b>Answer: A) S</b>
</Alert>

<Alert status="info">
<b>Reason:</b> Size <b>S</b> has the highest return rate at <b><Value data={q9} column=val fmt=pct2/></b>. Smaller sizes may suffer from fit ambiguity (tighter fit tolerance) or higher returns from younger, more style-experimental buyers. Size-guide accuracy and fit-prediction models should prioritize S and M.
</Alert>

---

## Q10. Highest-Value Installment Plan

**Question:** Which installment plan has the highest average payment value per order?

<Alert status="positive">
<b>Answer: C) 6 kỳ</b>
</Alert>

<Alert status="info">
<b>Reason:</b> The 6-installment plan averages <b><Value data={q10} column=val fmt=num0/> VND</b> per order — higher than 1, 3, and 12 installments. Customers choosing 6 installments are likely buying higher-ticket items (premium products, larger baskets) and using installments to manage cash flow. This is the highest-LTV payment cohort.
</Alert>

---

## Summary

<Alert status="info">

**Key takeaways across all 10 questions:**
- <b>Customer behavior:</b> 55+ is the most loyal segment; median repeat gap is 144 days.
- <b>Products:</b> Standard has the highest margin; Streetwear suffers from wrong-size returns.
- <b>Traffic quality:</b> Email is the highest-intent channel (lowest bounce).
- <b>Promo intensity:</b> ~39% of order lines are discounted — margin discipline is critical.
- <b>Regional:</b> East drives the most revenue.
- <b>Payment:</b> 6-installment plans correlate with the highest order values.

</Alert>
