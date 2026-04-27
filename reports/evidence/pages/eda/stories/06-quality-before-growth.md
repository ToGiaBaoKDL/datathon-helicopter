---
title: Quality Before Growth
---

# Quality Before Growth

<Alert status="warning">
<b>The question:</b> Return rate sits near <Value data={return_summary} column=avg_return_rate fmt=pct2/>. 
Which return reasons dominate? What share is <b>controllable</b> — fixable with operations, not psychology?
</Alert>

```sql return_summary
select
    round(avg(return_record_rate), 4) as avg_return_rate,
    round(avg(return_unit_rate), 4) as avg_return_unit_rate,
    sum(return_record_count) as total_return_records,
    sum(return_units) as total_return_units
from datathon_warehouse.mart_daily_returns_kpis
```

```sql return_reasons
select
    sum(defective_return_count) as defective,
    sum(wrong_size_return_count) as wrong_size,
    sum(not_as_described_return_count) as not_as_described,
    sum(changed_mind_return_count) as changed_mind,
    sum(late_delivery_return_count) as late_delivery,
    sum(defective_return_count + wrong_size_return_count) as controllable_returns,
    sum(defective_return_count + wrong_size_return_count + not_as_described_return_count + changed_mind_return_count + late_delivery_return_count) as total_returns
from datathon_warehouse.mart_daily_returns_kpis
```

```sql controllable_pct
select
    round(sum(defective_return_count + wrong_size_return_count)::double / nullif(sum(defective_return_count + wrong_size_return_count + not_as_described_return_count + changed_mind_return_count + late_delivery_return_count), 0), 4) as controllable_pct
from datathon_warehouse.mart_daily_returns_kpis
```

```sql return_reasons_unpivot
select 'defective' as reason, defective as returns from ${return_reasons}
union all
select 'wrong_size', wrong_size from ${return_reasons}
union all
select 'not_as_described', not_as_described from ${return_reasons}
union all
select 'changed_mind', changed_mind from ${return_reasons}
union all
select 'late_delivery', late_delivery from ${return_reasons}
order by returns desc
```

```sql monthly_return_trend
select
    sales_date,
    return_record_rate,
    return_unit_rate
from datathon_warehouse.mart_daily_returns_kpis
order by sales_date
```

```sql quality_correlation
select
    product_name,
    category,
    total_revenue,
    return_unit_rate,
    avg_rating,
    review_count
from datathon_warehouse.mart_product_reviews_summary
where review_count >= 5
  and total_revenue > 0
order by total_revenue desc
```

```sql refund_total
select
    round(sum(refund_amount), 0) as total_refund_amount,
    round(sum(return_units), 0) as total_return_units
from datathon_warehouse.mart_daily_returns_kpis
```

## 1. The Rate: One in Every ~20 Orders Returns

<Alert status="info">
The average return record rate is <b><Value data={return_summary} column=avg_return_rate fmt=pct2/></b>. 
That means roughly one in every <Value data={return_summary} column=avg_return_rate fmt=pct2/> orders generates a return record. 
The controllable share — defective + wrong_size — is <b><Value data={controllable_pct} column=controllable_pct fmt=pct2/></b> of all returns.
</Alert>

<Grid cols=2>
    <BigValue
        data={return_summary}
        value=avg_return_rate
        title="Avg Return Record Rate"
        fmt="pct2"
    />
    <BigValue
        data={return_summary}
        value=avg_return_unit_rate
        title="Avg Return Unit Rate"
        fmt="pct2"
    />
</Grid>

## 2. Root Causes: Operational Failures, Not Behavioral

<Alert status="info">
<b>Defective</b> and <b>wrong_size</b> are operational failures — supplier quality and sizing accuracy. 
Together they represent <Value data={controllable_pct} column=controllable_pct fmt=pct2/> of all returns. 
These are fixable. <b>Changed_mind</b> and <b>late_delivery</b> are harder to control.
</Alert>

<BarChart
    data={return_reasons_unpivot}
    x=reason
    y=returns
    title="Return Reasons by Total Count"
    subtitle="Defective + wrong_size = controllable operational failures"
    yAxisTitle="Return Records"
    yFmt="0"
/>

## 3. Quality Correlation: Rating vs Return Rate

<Alert status="info">
Products with low ratings and high return rates are a quality crisis. 
The scatter below maps every product with at least 5 reviews. 
The danger zone (rating below 3, return rate above 5%) is where immediate action is needed.
</Alert>

<BubbleChart
    data={quality_correlation}
    x=avg_rating
    y=return_unit_rate
    size=total_revenue
    title="Product Rating vs Return Rate"
    subtitle="Bubble size = total revenue. Danger zone = low rating + high returns"
    xAxisTitle="Average Rating"
    yAxisTitle="Return Unit Rate"
    yFmt="pct2"
    xFmt="0.0"
>
    <ReferenceLine y=0.05 label="5% Alert" hideValue=true color=negative/>
    <ReferenceLine x=3.0 label="3.0 Rating" hideValue=true color=negative/>
</BubbleChart>

## 4. Monthly Trend: Persistent, Not Spiking

<Alert status="info">
Return rate is structurally elevated — it does not spike; it persists. 
This is a baseline quality problem, not a one-off incident.
</Alert>

<LineChart
    data={monthly_return_trend}
    x=sales_date
    y=return_record_rate
    title="Daily Return Record Rate Over Time"
    subtitle="Persistent ~5% baseline — a structural quality issue"
    yAxisTitle="Return Record Rate"
    yFmt="pct2"
>
    <ReferenceLine y=0.05 label="5% Threshold" hideValue=true color=negative lineType=dashed/>
</LineChart>

## 5. The Cost: Total Refund Exposure

<Alert status="info">
Defective and wrong_size returns represent a direct refund cost plus reverse logistics, re-stocking, and customer service overhead. 
The total lifetime refund amount across all returns is substantial.
</Alert>

<Grid cols=2>
    <BigValue
        data={refund_total}
        value=total_return_units
        title="Total Returned Units"
        fmt="0"
    />
    <BigValue
        data={refund_total}
        value=total_refund_amount
        title="Total Refund Amount"
        fmt="num0"
    />
</Grid>

## The Verdict

<Alert status="positive">
<b>Action:</b> <Value data={controllable_pct} column=controllable_pct fmt=pct2/> of returns are controllable. 
Implement supplier QC checks to reduce defective rates. 
Deploy detailed sizing guides and fit tools for top-returned categories. 
Target: cut controllable returns by 50% within 6 months.
</Alert>
