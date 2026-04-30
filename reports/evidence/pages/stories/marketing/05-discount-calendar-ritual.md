---
title: The Discount Calendar Ritual
---

<Alert status="warning">
<b>The question:</b> Every year the business runs the same percentage promos at the same <Value data={percentage_discount} column=avg_pct_discount fmt=pct2/> average discount. 
Revenue from these campaigns has fallen <Value data={revenue_drop} column=revenue_drop_pct fmt=pct2/> since 2013. 
Is the discount calendar a revenue engine or a margin ritual?
</Alert>

```sql promo_trend
select
    date_part('year', start_date)::int as year,
    promo_type,
    count(*) as campaigns,
    round(avg(discount_rate), 4) as avg_discount,
    round(sum(total_net_revenue), 0) as total_revenue,
    round(sum(total_discount_amount), 0) as total_discount
from datathon_warehouse.mart_promotion_effectiveness
where total_orders > 0
group by 1, 2
order by year, promo_type
```

```sql promo_summary
select
    promo_type,
    count(*) as campaigns,
    round(avg(discount_rate), 4) as avg_discount,
    round(sum(total_net_revenue), 0) as total_revenue,
    round(sum(total_discount_amount), 0) as total_discount,
    round(sum(total_discount_amount)::double / nullif(sum(total_net_revenue + total_discount_amount), 0), 4) as effective_discount
from datathon_warehouse.mart_promotion_effectiveness
where total_orders > 0
group by 1
order by total_revenue desc
```

```sql percentage_discount
select round(avg(discount_rate), 4) as avg_pct_discount
from datathon_warehouse.mart_promotion_effectiveness
where promo_type = 'percentage'
  and total_orders > 0
```

```sql revenue_drop
select
    round(
        (sum(case when year = 2022 then total_revenue else 0 end) - sum(case when year = 2013 then total_revenue else 0 end))
        / nullif(sum(case when year = 2013 then total_revenue else 0 end), 0),
        4
    ) as revenue_drop_pct
from (
    select date_part('year', start_date)::int as year, sum(total_net_revenue) as total_revenue
    from datathon_warehouse.mart_promotion_effectiveness
    where total_orders > 0 and promo_type = 'percentage'
    group by 1
) t
```

```sql daily_discount_calendar
select
    sales_date,
    total_discount_amount as discount_amount
from datathon_warehouse.mart_forecast_daily_base
order by sales_date
```

```sql negative_by_category
select
    category,
    count(*) as total_skus,
    sum(case when realized_margin_rate < 0 then 1 else 0 end) as negative_skus,
    round(sum(case when realized_margin_rate < 0 then 1 else 0 end)::double / count(*), 4) as negative_pct,
    round(avg(realized_margin_rate), 4) as avg_margin
from datathon_warehouse.mart_product_lifetime_performance
where lifecycle_stage != 'never_sold'
group by 1
order by negative_pct desc
```

```sql category_discount_exposure
select
    coalesce(applicable_category, 'All Categories') as category,
    count(*) as campaigns,
    round(avg(discount_rate), 4) as avg_discount,
    round(sum(total_net_revenue), 0) as promo_revenue
from datathon_warehouse.mart_promotion_effectiveness
where total_orders > 0
group by 1
order by avg_discount desc
```

```sql what_if_discount_cut
with base as (
    select
        round(avg(discount_rate), 4) as current_discount,
        round(sum(total_net_revenue), 0) as total_promo_revenue,
        round(sum(total_discount_amount), 0) as total_discount,
        count(*) as campaign_count
    from datathon_warehouse.mart_promotion_effectiveness
    where total_orders > 0 and promo_type = 'percentage'
)
select
    current_discount,
    total_promo_revenue,
    total_discount,
    round(current_discount - 0.02, 4) as reduced_discount,
    round(total_discount * (current_discount - 0.02) / nullif(current_discount, 0), 0) as reduced_discount_amount,
    round(total_discount - reduced_discount_amount, 0) as margin_protected,
    round(total_promo_revenue + margin_protected, 0) as implied_revenue_if_elasticity_zero
from base
```

```sql discount_dow
select
    extract(dow from sales_date) as dow,
    case extract(dow from sales_date)
        when 0 then 'Sun'
        when 1 then 'Mon'
        when 2 then 'Tue'
        when 3 then 'Wed'
        when 4 then 'Thu'
        when 5 then 'Fri'
        when 6 then 'Sat'
    end as day_name,
    round(sum(total_discount_amount), 0) as total_discount,
    round(sum(revenue), 0) as total_revenue,
    round(sum(total_discount_amount)::double / nullif(sum(revenue), 0), 4) as discount_to_revenue_ratio
from datathon_warehouse.mart_forecast_daily_base
where sales_date is not null
  and extract(year from sales_date) >= 2013
  and extract(year from sales_date) <= 2022
group by 1, 2
order by 1
```

## 1. The Ritual: Same Discount, Every Year

<Alert status="info">
Percentage campaigns run like clockwork: <Value data={promo_summary} column=campaigns fmt=0/> campaigns, 
<Value data={promo_summary} column=avg_discount fmt=pct2/> discount, <Value data={promo_summary} column=total_revenue fmt=num0/> VND revenue. 
The discount rate has barely changed in a decade — a ritual, not a strategy.
</Alert>

<BarChart
    data={promo_trend}
    x=year
    y=avg_discount
    series=promo_type
    title="Average Discount Rate by Year and Promo Type"
    subtitle="Percentage discount is locked in a narrow band year after year"
    yAxisTitle="Discount Rate"
    yFmt="pct2"
/>

<AreaChart
    data={promo_trend}
    x=year
    y=total_revenue
    series=promo_type
    title="Promo Revenue by Year and Type"
    subtitle="Promo revenue is declining even as discount depth stays flat"
    yAxisTitle="Revenue (VND)"
    yFmt="num0"
/>

<Alert status="info">
The calendar below shows daily discount intensity. Recurring bright bands reveal the "ritual" — promo spikes happen on predictable dates year after year.
</Alert>

<CalendarHeatmap
    data={daily_discount_calendar}
    date=sales_date
    value=discount_amount
    title="Daily Discount Calendar"
    subtitle="Discount intensity by day — recurring bright bands reveal the ritual"
    valueFmt="num0"
/>

<Alert status="info">
The heatmap below reveals the weekly discount rhythm. Deep discount days may be misaligned with high-conversion days.
If the business discounts heavily on low-conversion days (weekends) and lightly on high-conversion days (weekdays),
promotional budget is being misallocated.
</Alert>

<BarChart
    data={discount_dow}
    x=day_name
    y=discount_to_revenue_ratio
    title="Discount-to-Revenue Ratio by Day of Week"
    subtitle="Higher ratio = more discount spend per revenue dollar. Misalignment with conversion days = wasted budget."
    yAxisTitle="Discount / Revenue"
    yFmt="pct2"
>
    <ReferenceLine y=0.05 label="5% Benchmark" hideValue=true color=info lineType=dashed/>
</BarChart>

## 2. The Decline: Promo Revenue Is Falling

<Alert status="info">
Percentage promo revenue peaked in 2013–2015 and has declined since.
The business is discounting at the same rate but generating less return — a classic diminishing-returns pattern.
</Alert>

<LineChart
    data={promo_trend}
    x=year
    y=total_revenue
    series=promo_type
    title="Promo Revenue Trend Over Time"
    subtitle="Percentage promo revenue peaked early and has declined since"
    yAxisTitle="Revenue (VND)"
    yFmt="num0"
/>

<Grid cols=2>
    <BigValue
        data={promo_summary}
        value=total_discount
        title="Total Discount Given"
        fmt="num0"
    />
    <BigValue
        data={promo_summary}
        value=effective_discount
        title="Effective Discount Rate"
        fmt="pct2"
    />
</Grid>

## 3. The Real Culprit: Product Margin, Not Promo Discount

<Alert status="info">
Streetwear has the highest share of loss-making SKUs (<Value data={negative_by_category} column=negative_pct fmt=pct2/>) 
but the lowest promo discount exposure. 
The margin problem is structural — pricing and COGS — not promotional.
</Alert>

<BarChart
    data={negative_by_category}
    x=category
    y=negative_pct
    title="Negative-Margin SKU Share by Category"
    subtitle="Streetwear leads in loss-making products despite low discount exposure"
    yAxisTitle="Share of SKU with Negative Margin"
    yFmt="pct2"
/>

<BarChart
    data={category_discount_exposure}
    x=category
    y=avg_discount
    title="Average Promo Discount by Category Scope"
    subtitle="Streetwear faces minimal discounting; All Categories promos dominate"
    yAxisTitle="Discount Rate"
    yFmt="pct2"
/>

## 4. What-If: Cut Discount Depth by 2 Points

<Alert status="info">
Percentage campaigns currently average <b><Value data={what_if_discount_cut} column=current_discount fmt=pct2/></b> discount,
spending <b><Value data={what_if_discount_cut} column=total_discount fmt=num0/></b> VND in total discounts.
If the average discount rate is reduced by 2 percentage points (to <Value data={what_if_discount_cut} column=reduced_discount fmt=pct2/>),
total discount spend drops to <b><Value data={what_if_discount_cut} column=reduced_discount_amount fmt=num0/></b> VND —
protecting <b><Value data={what_if_discount_cut} column=margin_protected fmt=num0/></b> VND in margin.
Even if demand elasticity is zero (no volume loss), this is pure margin gain.
</Alert>

<Grid cols=3>
    <BigValue
        data={what_if_discount_cut}
        value=current_discount
        title="Current Avg Discount"
        fmt="pct2"
    />
    <BigValue
        data={what_if_discount_cut}
        value=reduced_discount
        title="Reduced Discount"
        fmt="pct2"
    />
    <BigValue
        data={what_if_discount_cut}
        value=margin_protected
        title="Margin Protected"
        fmt="num0"
    />
</Grid>

## The Verdict

<Alert status="positive">
<b>Action:</b> The discount calendar is a ritual with diminishing returns. 
Percentage revenue has dropped <Value data={revenue_drop} column=revenue_drop_pct fmt=pct2/> since 2013 at the same discount depth. 
The margin crisis is not caused by discounting — it is caused by <Value data={negative_by_category} column=negative_skus fmt=0/> <a href="/stories/product/02-profitability-leak">negative-margin SKUs</a>, mostly in Streetwear. 
Cut the ritual: test lower discount rates (8–10%) or shift from site-wide percentage to category-specific fixed discounts. 
Fix pricing and COGS for Streetwear before blaming promotions.
</Alert>

## Deep Dive

- [Promotion Effectiveness](/eda/marketing/02-promotion-effectiveness)

