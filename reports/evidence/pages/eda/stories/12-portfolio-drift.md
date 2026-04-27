---
title: The Portfolio Drift
---

# The Portfolio Drift

<Alert status="warning">
<b>The question:</b> Streetwear generates the most revenue (<Value data={streetwear_stats} column=total_revenue fmt=num0/> VND) but has the lowest margin (<Value data={streetwear_stats} column=avg_margin_rate fmt=pct2/>).
GenZ has the highest margin (<Value data={genz_stats} column=avg_margin_rate fmt=pct2/>) but the smallest revenue (<Value data={genz_stats} column=total_revenue fmt=num0/> VND).
Is the portfolio drifting toward low-margin volume?
</Alert>

```sql category_summary
select
    category,
    round(sum(gross_revenue), 0) as total_revenue,
    round(avg(gross_margin_rate), 4) as avg_margin_rate,
    round(sum(gross_profit), 0) as total_gross_profit,
    round(avg(return_unit_rate), 4) as avg_return_rate,
    sum(order_count) as total_orders
from datathon_warehouse.mart_monthly_category_performance
group by 1
order by total_revenue desc
```

```sql streetwear_stats
select
    round(sum(gross_revenue), 0) as total_revenue,
    round(avg(gross_margin_rate), 4) as avg_margin_rate
from datathon_warehouse.mart_monthly_category_performance
where category = 'Streetwear'
```

```sql genz_stats
select
    round(sum(gross_revenue), 0) as total_revenue,
    round(avg(gross_margin_rate), 4) as avg_margin_rate
from datathon_warehouse.mart_monthly_category_performance
where category = 'GenZ'
```

```sql monthly_category_trend
select
    month_start_date,
    category,
    gross_revenue,
    gross_margin_rate
from datathon_warehouse.mart_monthly_category_performance
order by month_start_date, category
```

```sql monthly_return_trend
select
    month_start_date,
    category,
    return_unit_rate
from datathon_warehouse.mart_monthly_category_performance
order by month_start_date, category
```

```sql margin_lift_value
select
    round(sum(gross_revenue), 0) as streetwear_revenue,
    round(sum(gross_revenue) * 0.02, 0) as two_point_lift
from datathon_warehouse.mart_monthly_category_performance
where category = 'Streetwear'
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
    subtitle="Monthly margin by category — all segments trail the 15% target"
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

## The Verdict

<Alert status="positive">
<b>Action:</b> The revenue engine (Streetwear, <Value data={streetwear_stats} column=total_revenue fmt=num0/> VND) is the lowest-margin category (<Value data={streetwear_stats} column=avg_margin_rate fmt=pct2/>). 
High-margin categories (GenZ <Value data={genz_stats} column=avg_margin_rate fmt=pct2/>, Casual) are small. 
Grow GenZ/Casual marketing share. Negotiate Streetwear COGS with suppliers. Review Streetwear pricing power — even a 2-point margin lift on <Value data={margin_lift_value} column=streetwear_revenue fmt=num0/> VND is <Value data={margin_lift_value} column=two_point_lift fmt=num0/> VND.
</Alert>
