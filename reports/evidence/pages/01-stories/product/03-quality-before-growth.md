---
title: Quality Before Growth
---

<Alert status="warning">
<b>The question:</b> Return rate sits near <Value data={return_summary} column=avg_return_rate fmt=pct2/>. 
Which return reasons dominate? What share is <b>controllable</b> — fixable with operations, not psychology?
</Alert>

```sql return_summary
select
    round(avg(return_record_rate), 4) as avg_return_rate,
    round(avg(return_unit_rate), 4) as avg_return_unit_rate,
    sum(return_record_count) as total_return_records,
    sum(return_units) as total_return_units,
    round(1.0 / nullif(avg(return_record_rate), 0), 0) as orders_per_return
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

```sql top_returned_products
select
    product_name,
    category,
    round(total_revenue, 0) as total_revenue,
    round(return_unit_rate, 4) as return_unit_rate,
    total_units_sold
from datathon_warehouse.mart_product_lifetime_performance
where lifecycle_stage != 'never_sold'
  and total_revenue > 0
order by return_unit_rate desc
limit 10
```

```sql refund_total
select
    round(sum(refund_amount), 0) as total_refund_amount,
    round(sum(return_units), 0) as total_return_units
from datathon_warehouse.mart_daily_returns_kpis
```

```sql refund_revenue_pct
select
    round(
        (select sum(refund_amount) from datathon_warehouse.mart_daily_returns_kpis)
        / nullif((select sum(revenue) from datathon_warehouse.mart_daily_executive_kpis), 0),
        4
    ) as refund_pct
```

```sql refund_monthly_trend
select
    date_trunc('month', r.sales_date) as month_start,
    round(sum(r.refund_amount), 0) as monthly_refund,
    round(sum(r.refund_amount)::double / nullif(sum(e.revenue), 0), 4) as refund_pct_of_revenue
from datathon_warehouse.mart_daily_returns_kpis r
join datathon_warehouse.mart_daily_executive_kpis e on r.sales_date = e.sales_date
group by 1
order by 1
```

```sql what_if_quality
with base as (
    select
        sum(defective_return_count + wrong_size_return_count) as controllable_returns,
        sum(refund_amount) as total_refund,
        sum(defective_return_count + wrong_size_return_count + not_as_described_return_count + changed_mind_return_count + late_delivery_return_count) as total_returns,
        round(sum(refund_amount)::double / nullif(sum(return_record_count), 0), 0) as avg_refund_per_return
    from datathon_warehouse.mart_daily_returns_kpis
)
select
    controllable_returns,
    total_refund,
    avg_refund_per_return,
    round(controllable_returns * 0.5, 0) as reducible_returns,
    round(reducible_returns * avg_refund_per_return, 0) as refund_savings,
    round(refund_savings::double / nullif((select sum(revenue) from datathon_warehouse.mart_daily_executive_kpis), 0), 4) as revenue_pct_saved
from base
```

```sql rating_distribution
select
    category,
    case
        when avg_rating >= 4.5 then 'Excellent (4.5-5.0)'
        when avg_rating >= 3.5 then 'Good (3.5-4.4)'
        when avg_rating >= 2.5 then 'Fair (2.5-3.4)'
        else 'Poor (Below 2.5)'
    end as rating_bucket,
    count(*) as product_count,
    avg(return_unit_rate) as avg_return_rate,
    avg(realized_margin_rate) as avg_margin_rate
from datathon_warehouse.mart_product_reviews_summary
where review_count > 0
group by 1, 2
order by 1,
    case
        when rating_bucket = 'Excellent (4.5-5.0)' then 1
        when rating_bucket = 'Good (3.5-4.4)' then 2
        when rating_bucket = 'Fair (2.5-3.4)' then 3
        else 4
    end
```

```sql rating_bucket_summary
select
    case
        when avg_rating >= 4.5 then 'Excellent (4.5-5.0)'
        when avg_rating >= 3.5 then 'Good (3.5-4.4)'
        when avg_rating >= 2.5 then 'Fair (2.5-3.4)'
        else 'Poor (Below 2.5)'
    end as rating_bucket,
    count(*) as product_count,
    avg(return_unit_rate) as avg_return_rate
from datathon_warehouse.mart_product_reviews_summary
where review_count > 0
group by 1
order by
    case
        when rating_bucket = 'Excellent (4.5-5.0)' then 1
        when rating_bucket = 'Good (3.5-4.4)' then 2
        when rating_bucket = 'Fair (2.5-3.4)' then 3
        else 4
    end
```

```sql category_quality
select
    category,
    count(*) as products_with_reviews,
    sum(review_count * avg_rating) / sum(review_count) as avg_rating,
    avg(return_unit_rate) as avg_return_rate,
    avg(realized_margin_rate) as avg_margin_rate,
    sum(review_count) as total_reviews,
    avg(low_rating_rate) as avg_low_rating_rate
from datathon_warehouse.mart_product_reviews_summary
where review_count > 0
group by 1
order by avg_rating desc
```

```sql review_trend
select
    month_start_date,
    category,
    review_count,
    avg_rating,
    low_rating_rate
from datathon_warehouse.mart_monthly_reviews_trend
order by month_start_date
```

```sql high_risk_products
select
    product_name,
    category,
    avg_rating,
    return_unit_rate,
    realized_margin_rate,
    review_count,
    total_revenue
from datathon_warehouse.mart_product_reviews_summary
where review_count >= 5
  and avg_rating < 3.0
order by return_unit_rate desc
```

```sql poor_rated_count
select count(*) as poor_products
from datathon_warehouse.mart_product_reviews_summary
where review_count >= 5
  and avg_rating < 3.0
```

```sql return_rate_ratio
select
    round(
        max(case when rating_bucket = 'Poor (Below 2.5)' then avg_return_rate end)
        / nullif(max(case when rating_bucket = 'Excellent (4.5-5.0)' then avg_return_rate end), 0),
        1
    ) as poor_to_excellent_ratio
from ${rating_bucket_summary}
```

```sql no_reviews
select
    category,
    count(*) as products_without_reviews,
    avg(total_revenue) as avg_revenue,
    avg(return_unit_rate) as avg_return_rate
from datathon_warehouse.mart_product_reviews_summary
where review_count = 0
group by 1
order by products_without_reviews desc
```

```sql no_reviews_total
select count(*) as products_without_reviews
from datathon_warehouse.mart_product_reviews_summary
where review_count = 0
```

## 1. The Rate: One in Every <Value data={return_summary} column=orders_per_return fmt=0/> Orders Returns

<Alert status="info">
The average return record rate is <b><Value data={return_summary} column=avg_return_rate fmt=pct2/></b>.
That means roughly 1 in every <Value data={return_summary} column=orders_per_return fmt=0/> orders generates a return record.
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

## 2.5. Rating Distribution: Where Quality Clusters

<Alert status="info">
Most reviewed products fall into the Good or Excellent buckets. 
However, the <b>Poor</b> bucket — while small — carries a disproportionately high return rate. 
These outliers are a small group with outsized operational impact.
</Alert>

<BarChart
    data={rating_distribution}
    x=rating_bucket
    y=product_count
    series=category
    sort=false
    title="Product Count by Rating Bucket"
    subtitle="Quality distribution across categories"
    yAxisTitle="Products"
    yFmt="0"
/>

## 2.6. Return Rate by Rating Bucket: The Poor-Rated Penalty

<Alert status="warning">
Lower-rated products drive return rates <b><Value data={return_rate_ratio} column=poor_to_excellent_ratio fmt=0.0/>×</b> the Excellent tier
(<Value data={rating_bucket_summary} column=avg_return_rate row=3 fmt=pct2/> Poor vs <Value data={rating_bucket_summary} column=avg_return_rate row=0 fmt=pct2/> Excellent).
Fixing or delisting Poor-rated SKUs is high-ROI housekeeping.
</Alert>

<BarChart
    data={rating_distribution}
    x=rating_bucket
    y=avg_return_rate
    series=category
    sort=false
    title="Average Return Rate by Rating Bucket"
    subtitle="Lower ratings correlate with higher returns"
    yAxisTitle="Return Rate"
    yFmt="pct2"
>
    <ReferenceLine y=0.05 label="5% Alert" hideValue=true color=negative lineType=dashed/>
</BarChart>

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

<Alert status="warning">
The products below have the highest return unit rates in the catalog. 
Even if they generate revenue, the return cost erodes or destroys margin.
These are the highest-priority targets for QC and sizing-guide fixes.
</Alert>

<DataTable data={top_returned_products} rows=10>
    <Column id=product_name title="Product"/>
    <Column id=category title="Category"/>
    <Column id=total_revenue title="Revenue" fmt=num0/>
    <Column id=return_unit_rate title="Return Rate" fmt=pct2/>
    <Column id=total_units_sold title="Units Sold" fmt=0/>
</DataTable>

## 3.5. Category Quality Rank: Which Categories Satisfy Customers?

<Alert status="info">
Category-level average rating reveals where customer satisfaction is strongest and weakest. 
Categories with low ratings and high return rates need immediate quality investment.
</Alert>

<BarChart
    data={category_quality}
    x=category
    y=avg_rating
    title="Average Rating by Category"
    subtitle="Category-level customer satisfaction rank"
    yAxisTitle="Avg Rating"
    yFmt="0.00"
>
    <ReferenceLine y=3.5 label="3.5 Floor" hideValue=true color=warning lineType=dashed/>
</BarChart>

<BarChart
    data={category_quality}
    x=category
    y=avg_return_rate
    title="Average Return Rate by Category"
    subtitle="Quality problems surface as returns"
    yAxisTitle="Return Rate"
    yFmt="pct2"
>
    <ReferenceLine y=0.05 label="5% Alert" hideValue=true color=negative lineType=dashed/>
</BarChart>

## 3.6. High-Risk Products: Rating Below 3.0

<Alert status="warning">
<Value data={poor_rated_count} column=poor_products fmt=0/> products have avg_rating below 3.0 with at least 5 reviews. 
They are actively damaging customer trust and margin. Consider delisting, repricing, or switching suppliers.
</Alert>

<DataTable data={high_risk_products} rows=10>
    <Column id=product_name title="Product"/>
    <Column id=category title="Category"/>
    <Column id=avg_rating title="Rating" fmt=0.0/>
    <Column id=return_unit_rate title="Return Rate" fmt=pct2/>
    <Column id=realized_margin_rate title="Margin" fmt=pct2/>
    <Column id=review_count title="Reviews" fmt=0/>
    <Column id=total_revenue title="Revenue" fmt=num0/>
</DataTable>

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
    subtitle="Return rate stays structurally elevated over time"
    yAxisTitle="Return Record Rate"
    yFmt="pct2"
>
    <ReferenceLine y=0.05 label="5% Threshold" hideValue=true color=negative lineType=dashed/>
</LineChart>

## 4.5. Review Signals: Volume and Rating Trends

<Alert status="info">
Review volume is a proxy for purchase volume and engagement. 
A declining review trend with flat revenue suggests fewer but bigger orders — or fewer customers leaving feedback, a warning sign for engagement.
</Alert>

<LineChart
    data={review_trend}
    x=month_start_date
    y=review_count
    series=category
    title="Monthly Review Volume by Category"
    subtitle="Customer feedback trend over time"
    yAxisTitle="Review Count"
    yFmt="0"
/>

<LineChart
    data={review_trend}
    x=month_start_date
    y=avg_rating
    series=category
    title="Average Rating Trend by Category"
    subtitle="Track category quality evolution"
    yAxisTitle="Avg Rating"
    yFmt="0.00"
>
    <ReferenceLine y=3.5 label="3.5 Floor" hideValue=true color=warning lineType=dashed/>
</LineChart>

## 4.6. Products Without Reviews: The Blind Spot

<Alert status="warning">
<Value data={no_reviews_total} column=products_without_reviews fmt=0/> products have zero reviews. 
If they generate revenue but no feedback, the business is flying blind on quality for a significant part of the catalog.
</Alert>

<BarChart
    data={no_reviews}
    x=category
    y=products_without_reviews
    title="Products Without Reviews by Category"
    subtitle="Blind spots in quality monitoring"
    yAxisTitle="Products"
    yFmt="0"
/>

<BarChart
    data={no_reviews}
    x=category
    y=avg_return_rate
    title="Avg Return Rate of No-Review Products"
    subtitle="Silent products may still carry return risk"
    yAxisTitle="Return Rate"
    yFmt="pct2"
>
    <ReferenceLine y=0.05 label="5% Alert" hideValue=true color=negative lineType=dashed/>
</BarChart>

## 5. The Cost: Total Refund Exposure

<Alert status="info">
Defective and wrong_size returns represent a direct refund cost plus reverse logistics, re-stocking, and customer service overhead.
The total lifetime refund amount across all returns is substantial.
</Alert>

<Grid cols=3>
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
    <BigValue
        data={refund_revenue_pct}
        value=refund_pct
        title="Refund as % of Revenue"
        fmt="pct2"
    />
</Grid>

<Alert status="info">
Refund as a share of revenue fluctuates month-to-month but shows a persistent baseline drain.
When refund % spikes above trend, investigate whether a specific batch or supplier caused the quality degradation.
</Alert>

<LineChart
    data={refund_monthly_trend}
    x=month_start
    y=refund_pct_of_revenue
    title="Monthly Refund as % of Revenue"
    subtitle="Persistent refund drain over time — quality is a structural cost"
    yAxisTitle="Refund % of Revenue"
    yFmt="pct2"
>
    <ReferenceLine y=0.05 label="5% Alert" hideValue=true color=warning lineType=dashed/>
</LineChart>

## 6. What-If: Cutting Controllable Returns by Half

<Alert status="info">
Controllable returns (defective + wrong_size) total <Value data={what_if_quality} column=controllable_returns fmt=0/> records.
Cutting this by 50% prevents <Value data={what_if_quality} column=reducible_returns fmt=0/> returns
and saves <Value data={what_if_quality} column=refund_savings fmt=num0/> VND in refunds.
That is <Value data={what_if_quality} column=revenue_pct_saved fmt=pct2/> of total revenue protected.
</Alert>

<Grid cols=3>
    <BigValue
        data={what_if_quality}
        value=controllable_returns
        title="Controllable Returns"
        fmt="0"
    />
    <BigValue
        data={what_if_quality}
        value=reducible_returns
        title="50% Reduction"
        fmt="0"
    />
    <BigValue
        data={what_if_quality}
        value=refund_savings
        title="Refund Savings (VND)"
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

## Deep Dive

- [Reviews And Quality](/02-eda/product/03-reviews-and-quality)
- [Fulfillment And Returns](/02-eda/operations/01-fulfillment-and-returns)

