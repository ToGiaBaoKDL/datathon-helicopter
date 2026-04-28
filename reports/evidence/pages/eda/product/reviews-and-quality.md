---
title: Reviews and Product Quality Signals
---

# Reviews and Product Quality Signals

This page connects customer review ratings with product performance, return rates, and margin health. 
Low ratings are early warning signals for quality crises before they hit return and margin metrics.

```sql _categories
select distinct category from datathon_warehouse.mart_product_reviews_summary order by 1
```

<Dropdown
    name=cat_filter
    data={_categories}
    value=category
    multiple=true
    selectAllByDefault=true
    title="Category"
/>

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
  and category in ${inputs.cat_filter.value}
group by 1, 2
order by 1,
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
  and category in ${inputs.cat_filter.value}
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
where category in ${inputs.cat_filter.value}
order by month_start_date
```

```sql rating_vs_return
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
  and category in ${inputs.cat_filter.value}
order by total_revenue desc
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
  and category in ${inputs.cat_filter.value}
order by return_unit_rate desc
```

```sql poor_rated_count
select count(*) as poor_products
from datathon_warehouse.mart_product_reviews_summary
where review_count >= 5
  and avg_rating < 3.0
  and category in ${inputs.cat_filter.value}
```

```sql no_reviews
select
    category,
    count(*) as products_without_reviews,
    avg(total_revenue) as avg_revenue,
    avg(return_unit_rate) as avg_return_rate
from datathon_warehouse.mart_product_reviews_summary
where review_count = 0
  and category in ${inputs.cat_filter.value}
group by 1
order by products_without_reviews desc
```

## Rating Distribution by Category

<Alert status="info">
Rating distribution reveals category-level quality consistency.
Only a small share of reviewed products fall into the "Poor" rating bucket, but these outliers carry
a disproportionately high return rate — roughly double the Good/Excellent tier. They are a small group with outsized impact.
</Alert>

<BarChart
    data={rating_distribution}
    x=rating_bucket
    y=product_count
    series=category
    sort=false
    title="Product Count by Rating Bucket"
    subtitle="Quality distribution across categories"
    yAxisTitle="Product Count"
    yFmt="0"
/>

<BarChart
    data={rating_distribution}
    x=rating_bucket
    y=avg_return_rate
    series=category
    sort=false
    title="Average Return Rate by Rating Bucket"
    subtitle="Lower-rated products drive higher returns"
    yAxisTitle="Return Rate"
    yFmt="pct2"
/>

## Category Quality Overview

<Alert status="warning">
Poor-rated products show return rates roughly double the Good/Excellent tier. 
While only a tiny fraction of reviewed products fall into this bucket, they generate disproportionate 
logistics cost and reputation risk. Delisting or repricing these SKUs is high-ROI housekeeping.
</Alert>

<BarChart
    data={category_quality}
    x=category
    y=avg_rating
    title="Average Rating by Category"
    subtitle="Category-level customer satisfaction"
    yAxisTitle="Avg Rating"
    yFmt="0.00"
/>

<BarChart
    data={category_quality}
    x=category
    y=avg_return_rate
    title="Average Return Rate by Category"
    subtitle="Quality problems surface as returns"
    yAxisTitle="Return Rate"
    yFmt="pct2"
/>

## Review Volume Trend

<Alert status="info">
Review volume is a proxy for purchase volume and engagement. 
A declining review trend in a category with flat revenue suggests fewer but bigger orders — 
or fewer customers leaving feedback, which is a warning sign for engagement.
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
/>

## Rating vs Return Rate Correlation

<Alert status="info">
Each dot is a product. The overall correlation between rating and return rate is weak, 
because most products cluster in the Good/Excellent range with similar return profiles. 
However, the <Value data={poor_rated_count} column=poor_products fmt=0/> Poor-rated products (bottom-left cluster) consistently show elevated returns. 
Focus attention on the bottom-right outliers: low rating + high return = immediate delist candidates.
</Alert>

<BubbleChart
    data={rating_vs_return}
    x=avg_rating
    y=return_unit_rate
    series=category
    size=total_revenue
    title="Product Rating vs Return Rate"
    subtitle="Bubble size = total revenue. Bottom-right = quality crisis."
    xAxisTitle="Average Rating"
    yAxisTitle="Return Unit Rate"
    xFmt="0.0"
    yFmt="pct2"
>
    <ReferenceLine y=0.05 label="5% Alert" hideValue=true color=warning/>
    <ReferenceArea xMin=0 xMax=3 yMin=0.05 label="Danger Zone" color=negative opacity=0.20 border=true/>
</BubbleChart>

## High-Risk Products

<Alert status="warning">
These products have avg_rating below 3.0 and significant review volume (5 or more reviews).
They are actively damaging customer trust and margin. Consider delisting, repricing, or switching suppliers.
</Alert>

<DataTable data={high_risk_products} rows=10 />

## Products Without Reviews

<Alert status="info">
Products with zero reviews may be new, low-volume, or have a broken review invitation flow. 
If they generate revenue but no feedback, you are flying blind on quality.
</Alert>

<BarChart
    data={no_reviews}
    x=category
    y=products_without_reviews
    title="Products Without Reviews by Category"
    subtitle="Blind spots in quality monitoring"
    yAxisTitle="Product Count"
    yFmt="0"
/>
