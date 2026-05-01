---
title: The Portfolio Drift
---

<Alert status="warning">
<b>The question:</b> Streetwear generates the most revenue (<Value data={streetwear_stats} column=total_revenue fmt=num0/> VND) but has the lowest margin (<Value data={streetwear_stats} column=avg_margin_rate fmt=pct2/>).
GenZ has the highest margin (<Value data={genz_stats} column=avg_margin_rate fmt=pct2/>) but the smallest revenue (<Value data={genz_stats} column=total_revenue fmt=num0/> VND).
Is the portfolio drifting toward low-margin volume?
</Alert>

```sql category_summary
select
    category,
    round(sum(gross_revenue), 0) as total_revenue,
    round(sum(gross_profit)::double / nullif(sum(gross_revenue), 0), 4) as avg_margin_rate,
    round(sum(gross_profit), 0) as total_gross_profit,
    round(sum(return_units)::double / nullif(sum(sold_units), 0), 4) as avg_return_rate,
    sum(order_count) as total_orders
from datathon_warehouse.mart_monthly_category_performance
group by 1
order by total_revenue desc
```

```sql streetwear_stats
select
    round(sum(gross_revenue), 0) as total_revenue,
    round(sum(gross_profit)::double / nullif(sum(gross_revenue), 0), 4) as avg_margin_rate
from datathon_warehouse.mart_monthly_category_performance
where category = 'Streetwear'
```

```sql genz_stats
select
    round(sum(gross_revenue), 0) as total_revenue,
    round(sum(gross_profit)::double / nullif(sum(gross_revenue), 0), 4) as avg_margin_rate
from datathon_warehouse.mart_monthly_category_performance
where category = 'GenZ'
```

```sql monthly_category_trend
select
    month_start_date,
    category,
    round(sum(gross_revenue), 0) as gross_revenue,
    round(sum(gross_profit)::double / nullif(sum(gross_revenue), 0), 4) as gross_margin_rate
from datathon_warehouse.mart_monthly_category_performance
group by 1, 2
order by 1, 2
```

```sql monthly_return_trend
select
    month_start_date,
    category,
    round(sum(return_units)::double / nullif(sum(sold_units), 0), 4) as return_unit_rate
from datathon_warehouse.mart_monthly_category_performance
group by 1, 2
order by 1, 2
```

```sql margin_lift_value
select
    round(sum(gross_revenue), 0) as streetwear_revenue,
    round(sum(gross_revenue) * 0.02, 0) as two_point_lift
from datathon_warehouse.mart_monthly_category_performance
where category = 'Streetwear'
```

```sql top_revenue_products
select
    product_name,
    category,
    round(total_revenue, 0) as total_revenue,
    round(realized_margin_rate, 4) as realized_margin_rate,
    round(return_unit_rate, 4) as return_unit_rate,
    round(revenue_share_in_category, 4) as revenue_share_in_category,
    lifecycle_stage
from datathon_warehouse.mart_product_lifetime_performance
where lifecycle_stage != 'never_sold'
  and total_revenue > 0
order by total_revenue desc
limit 10
```

```sql top_products_concentration
with top10 as (
    select total_revenue
    from datathon_warehouse.mart_product_lifetime_performance
    where lifecycle_stage != 'never_sold'
    order by total_revenue desc
    limit 10
)
select
    round(sum(t.total_revenue), 0) as top10_revenue,
    round(sum(t.total_revenue) / (select sum(total_revenue) from datathon_warehouse.mart_product_lifetime_performance where lifecycle_stage != 'never_sold'), 4) as top10_share
from top10 t
```

```sql category_share_trend
with monthly as (
    select
        month_start_date,
        category,
        sum(gross_revenue) as gross_revenue
    from datathon_warehouse.mart_monthly_category_performance
    group by 1, 2
)
select
    month_start_date,
    category,
    round(gross_revenue::double / sum(gross_revenue) over (partition by month_start_date), 4) as revenue_share
from monthly
order by month_start_date, category
```

```sql what_if_mix
with base as (
    select
        sum(case when category = 'Streetwear' then gross_revenue else 0 end) as streetwear_revenue,
        sum(case when category = 'GenZ' then gross_revenue else 0 end) as genz_revenue,
        sum(case when category = 'Streetwear' then gross_profit else 0 end) / nullif(sum(case when category = 'Streetwear' then gross_revenue else 0 end), 0) as streetwear_margin,
        sum(case when category = 'GenZ' then gross_profit else 0 end) / nullif(sum(case when category = 'GenZ' then gross_revenue else 0 end), 0) as genz_margin,
        sum(gross_revenue) as total_revenue,
        sum(gross_profit) as total_gross_profit
    from datathon_warehouse.mart_monthly_category_performance
)
select
    total_revenue,
    total_gross_profit,
    round(total_gross_profit::double / nullif(total_revenue, 0), 4) as current_margin,
    streetwear_revenue,
    streetwear_margin,
    genz_margin,
    round(streetwear_revenue * 0.10, 0) as shift_amount,
    round((total_gross_profit + shift_amount * (genz_margin - streetwear_margin)) / nullif(total_revenue, 0), 4) as new_margin,
    round(new_margin - current_margin, 4) as margin_lift,
    round(shift_amount * (genz_margin - streetwear_margin), 0) as profit_lift
from base
```

## 1. Category Revenue: Streetwear Dominates

<Alert status="info">
Streetwear is the revenue engine — but it is also the lowest-margin category. 
GenZ and Casual are high-margin but tiny. The portfolio is heavily skewed toward volume over profit.
</Alert>

<BarChart
    data={category_summary}
    x=category
    y=total_revenue
    title="Total Revenue by Category"
    subtitle="Streetwear dominates; high-margin categories are small"
    yAxisTitle="Revenue (VND)"
    yFmt="num0"
/>

## 1.5. Revenue Concentration: The Top 10 Products

<Alert status="info">
The top 10 products generate <b><Value data={top_products_concentration} column=top10_share fmt=pct2/></b> of total sold-product revenue. 
If these products face stockout or quality issues, the revenue impact is disproportionate. 
Monitor margin and return rate of top sellers closely.
</Alert>

<DataTable data={top_revenue_products} rows=10>
    <Column id=product_name title="Product"/>
    <Column id=category title="Category"/>
    <Column id=total_revenue title="Revenue" fmt=num0/>
    <Column id=realized_margin_rate title="Margin" fmt=pct2/>
    <Column id=return_unit_rate title="Return Rate" fmt=pct2/>
    <Column id=revenue_share_in_category title="Category Share" fmt=pct2/>
    <Column id=lifecycle_stage title="Lifecycle"/>
</DataTable>

## 2. Category Margin: The Inverse Relationship

<Alert status="info">
The revenue leader (Streetwear, <Value data={streetwear_stats} column=avg_margin_rate fmt=pct2/>) is the margin laggard. 
The margin leader (GenZ, <Value data={genz_stats} column=avg_margin_rate fmt=pct2/>) is the revenue laggard. 
This is classic portfolio drift: growth is coming from the least profitable segment.
</Alert>

<BarChart
    data={category_summary}
    x=category
    y=avg_margin_rate
    title="Average Gross Margin Rate by Category"
    subtitle="Streetwear margin lags high-margin categories by a wide gap"
    yAxisTitle="Margin Rate"
    yFmt="pct2"
>
    <ReferenceLine y=0.15 label="15% Target" hideValue=true color=positive lineType=dashed/>
</BarChart>

## 3. Revenue Trajectory: Is the Gap Widening?

<Alert status="info">
Monthly revenue by category shows whether Streetwear is pulling further ahead or whether high-margin categories are catching up.
</Alert>

<LineChart
    data={monthly_category_trend}
    x=month_start_date
    y=gross_revenue
    series=category
    title="Monthly Gross Revenue by Category"
    subtitle="Monthly revenue by category — Streetwear leads throughout"
    yAxisTitle="Revenue (VND)"
    yFmt="num0"
/>

<AreaChart
    data={category_share_trend}
    x=month_start_date
    y=revenue_share
    series=category
    title="Revenue Share by Category Over Time"
    subtitle="Portfolio drift: is Streetwear share growing while GenZ shrinks?"
    yAxisTitle="Share of Total Revenue"
    yFmt="pct2"
/>

## 4. Margin Trajectory: Is Streetwear Recovering?

<Alert status="info">
Even if Streetwear revenue grows, margin trajectory matters. A flat or declining margin means volume without profit improvement.
</Alert>

<LineChart
    data={monthly_category_trend}
    x=month_start_date
    y=gross_margin_rate
    series=category
    title="Monthly Gross Margin Rate by Category"
    subtitle="All categories fall short of the margin target"
    yAxisTitle="Margin Rate"
    yFmt="pct2"
>
    <ReferenceLine y=0.15 label="15% Target" hideValue=true color=positive lineType=dashed/>
</LineChart>

## 5. Return Rate by Category: Quality Adds Cost

<Alert status="info">
Return rate erodes margin. If Streetwear has high returns, that partly explains its low realized margin.
</Alert>

<LineChart
    data={monthly_return_trend}
    x=month_start_date
    y=return_unit_rate
    series=category
    title="Monthly Return Unit Rate by Category"
    subtitle="Returns erode margin — which categories bleed the most?"
    yAxisTitle="Return Unit Rate"
    yFmt="pct2"
>
    <ReferenceLine y=0.05 label="5% Alert" hideValue=true color=negative lineType=dashed/>
</LineChart>

## 6. What-If: Shifting Revenue Mix

<Alert status="info">
The portfolio currently earns <Value data={what_if_mix} column=current_margin fmt=pct2/> gross margin.
If 10% of Streetwear revenue shifted to GenZ,
portfolio margin would rise to <Value data={what_if_mix} column=new_margin fmt=pct2/>
(a <Value data={what_if_mix} column=margin_lift fmt=pct2/> lift),
adding <Value data={what_if_mix} column=profit_lift fmt=num0/> VND in gross profit
without growing total revenue.
</Alert>

<Grid cols=4>
    <BigValue
        data={what_if_mix}
        value=current_margin
        title="Current Portfolio Margin"
        fmt="pct2"
    />
    <BigValue
        data={what_if_mix}
        value=new_margin
        title="Shifted Portfolio Margin"
        fmt="pct2"
    />
    <BigValue
        data={what_if_mix}
        value=margin_lift
        title="Margin Lift"
        fmt="pct2"
    />
    <BigValue
        data={what_if_mix}
        value=profit_lift
        title="Profit Lift (VND)"
        fmt="num0"
    />
</Grid>

## The Verdict

<Alert status="positive">
<b>Action:</b> The revenue engine (Streetwear, <Value data={streetwear_stats} column=total_revenue fmt=num0/> VND) is the lowest-margin category (<Value data={streetwear_stats} column=avg_margin_rate fmt=pct2/>).
High-margin categories (GenZ <Value data={genz_stats} column=avg_margin_rate fmt=pct2/>, Casual) are small.
Grow GenZ/Casual marketing share. Negotiate Streetwear COGS with suppliers. Review Streetwear pricing power — even a 2-point margin lift on <Value data={margin_lift_value} column=streetwear_revenue fmt=num0/> VND is <Value data={margin_lift_value} column=two_point_lift fmt=num0/> VND.
See also <a href="/01-stories/product/02-profitability-leak">Story 02: The Profitability Leak</a> for negative-margin SKU analysis.
</Alert>

## Deep Dive

- [Category And Region Performance](/02-eda/product/02-category-and-region-performance)

