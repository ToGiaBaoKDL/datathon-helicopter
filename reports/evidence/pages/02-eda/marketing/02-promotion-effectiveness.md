---
title: Promotion Effectiveness
---

This page evaluates campaign performance by discount depth, channel, and revenue yield.

```sql _date_bounds
select sales_date from datathon_warehouse.mart_forecast_daily_base
```

```sql _promo_types
select distinct promo_type from datathon_warehouse.mart_promotion_effectiveness order by 1
```

```sql _promo_channels
select distinct promo_channel from datathon_warehouse.mart_promotion_effectiveness order by 1
```

<DateRange
    name=date_range
    data={_date_bounds}
    dates=sales_date
/>

<Dropdown
    name=type_filter
    data={_promo_types}
    value=promo_type
    multiple=true
    selectAllByDefault=true
    title="Promo Type"
/>

<Dropdown
    name=channel_filter
    data={_promo_channels}
    value=promo_channel
    multiple=true
    selectAllByDefault=true
    title="Promo Channel"
/>

```sql promo_summary
select
    promo_type,
    count(*) as campaigns,
    sum(total_orders) as total_orders,
    sum(total_net_revenue) as total_revenue,
    avg(discount_rate) as avg_discount_rate,
    sum(total_net_revenue) / sum(total_orders) as avg_aov
from datathon_warehouse.mart_promotion_effectiveness
where promo_type in ${inputs.type_filter.value}
  and promo_channel in ${inputs.channel_filter.value}
group by 1
order by total_revenue desc
```

```sql promo_type_pivot
select
    max(case when promo_type = 'percentage' then campaigns end) as pct_campaigns,
    max(case when promo_type = 'percentage' then total_revenue end) as pct_revenue,
    max(case when promo_type = 'percentage' then avg_discount_rate end) as pct_discount_rate,
    max(case when promo_type = 'fixed' then campaigns end) as fixed_campaigns,
    max(case when promo_type = 'fixed' then total_revenue end) as fixed_revenue,
    max(case when promo_type = 'fixed' then avg_discount_rate end) as fixed_discount_rate
from ${promo_summary}
```

```sql promo_timeline
select
    promo_name,
    promo_type,
    start_date,
    end_date,
    total_net_revenue as total_revenue,
    total_discount_amount as total_discount,
    discount_rate,
    total_orders
from datathon_warehouse.mart_promotion_effectiveness
where promo_type in ${inputs.type_filter.value}
  and promo_channel in ${inputs.channel_filter.value}
order by start_date
```

```sql promo_vs_discount
select
    promo_name,
    promo_type,
    discount_rate,
    total_net_revenue as total_revenue,
    total_orders
from datathon_warehouse.mart_promotion_effectiveness
where total_orders > 0
  and promo_type in ${inputs.type_filter.value}
  and promo_channel in ${inputs.channel_filter.value}
order by total_revenue desc
```

```sql channel_breakdown
select
    promo_channel,
    count(*) as campaigns,
    sum(total_orders) as total_orders,
    sum(total_net_revenue) as total_revenue,
    avg(discount_rate) as avg_discount_rate
from datathon_warehouse.mart_promotion_effectiveness
where promo_type in ${inputs.type_filter.value}
  and promo_channel in ${inputs.channel_filter.value}
group by 1
order by total_revenue desc
```

```sql avg_discount
select avg(discount_rate) as avg_discount
from datathon_warehouse.mart_promotion_effectiveness
where total_orders > 0
  and promo_type in ${inputs.type_filter.value}
  and promo_channel in ${inputs.channel_filter.value}
```

```sql daily_promo_pressure
select
    sales_date,
    total_discount_amount,
    promo_line_count,
    revenue
from datathon_warehouse.mart_forecast_daily_base
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
order by sales_date
```

```sql discount_heatmap_dow
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
    avg(total_discount_amount) as avg_discount
from datathon_warehouse.mart_forecast_daily_base
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
group by 1, 2
order by 1
```

```sql category_impact
select
    coalesce(applicable_category, 'All Categories') as category_scope,
    count(*) as campaigns,
    sum(total_net_revenue) as total_revenue,
    avg(discount_rate) as avg_discount_rate,
    sum(total_net_revenue) / nullif(sum(total_discount_amount), 0) as roi,
    sum(total_net_revenue) / sum(total_orders) as avg_aov
from datathon_warehouse.mart_promotion_effectiveness
where total_orders > 0
  and promo_type in ${inputs.type_filter.value}
  and promo_channel in ${inputs.channel_filter.value}
group by 1
order by total_revenue desc
```

```sql category_scatter
select
    coalesce(applicable_category, 'All Categories') as category_scope,
    promo_type,
    count(*) as campaigns,
    sum(total_net_revenue) as total_revenue,
    avg(discount_rate) as discount_rate,
    sum(total_net_revenue) / nullif(sum(total_discount_amount), 0) as roi,
    sum(total_orders) as total_orders
from datathon_warehouse.mart_promotion_effectiveness
where total_orders > 0
  and promo_type in ${inputs.type_filter.value}
  and promo_channel in ${inputs.channel_filter.value}
group by 1, 2
order by total_revenue desc
```

```sql category_detail
select
    applicable_category as category,
    promo_name,
    promo_type,
    total_net_revenue as total_revenue,
    discount_rate,
    total_orders
from datathon_warehouse.mart_promotion_effectiveness
where applicable_category is not null
  and total_orders > 0
  and promo_type in ${inputs.type_filter.value}
  and promo_channel in ${inputs.channel_filter.value}
order by applicable_category, total_revenue desc
```

```sql top_promo
select
    promo_name,
    promo_type,
    promo_channel,
    round(total_net_revenue, 0) as total_revenue,
    round(total_discount_amount, 0) as total_discount,
    round(discount_rate, 4) as discount_rate,
    total_orders,
    round(total_net_revenue / nullif(total_discount_amount, 0), 1) as roi
from datathon_warehouse.mart_promotion_effectiveness
where total_orders > 0
  and promo_type in ${inputs.type_filter.value}
  and promo_channel in ${inputs.channel_filter.value}
order by total_net_revenue desc
limit 1
```

```sql promo_ranking
select
    promo_name,
    promo_type,
    promo_channel,
    round(total_net_revenue, 0) as total_revenue,
    round(total_discount_amount, 0) as total_discount,
    round(discount_rate, 4) as discount_rate,
    total_orders,
    round(total_net_revenue / nullif(total_discount_amount, 0), 1) as roi
from datathon_warehouse.mart_promotion_effectiveness
where total_orders > 0
  and promo_type in ${inputs.type_filter.value}
  and promo_channel in ${inputs.channel_filter.value}
order by total_net_revenue desc
limit 10
```

## Promo Type Summary

<Alert status="info">
Percentage promos (<Value data={promo_type_pivot} column=pct_campaigns fmt=0/> campaigns) drive <Value data={promo_type_pivot} column=pct_revenue fmt=num0/> VND revenue at <Value data={promo_type_pivot} column=pct_discount_rate fmt=pct2/> average discount rate. 
Fixed promos (<Value data={promo_type_pivot} column=fixed_campaigns fmt=0/> campaigns) drive <Value data={promo_type_pivot} column=fixed_revenue fmt=num0/> VND at <Value data={promo_type_pivot} column=fixed_discount_rate fmt=pct2/> rate. Scale vs efficiency trade-off is clear.
</Alert>

<Alert status="positive">
Action: Fixed-discount campaigns show significantly higher ROI per discount VND than percentage campaigns, but with far fewer runs. 
Test expanding fixed-discount promos for high-margin categories where discount depth matters less.
</Alert>

<BarChart
    data={promo_summary}
    x=promo_type
    y=total_revenue
    title="Revenue by Promotion Type"
    subtitle="Scale vs efficiency trade-off by promo type"
    yAxisTitle="Net Revenue"
    yFmt="num0"
/>

<BarChart
    data={promo_summary}
    x=promo_type
    y=avg_discount_rate
    title="Average Discount Rate by Type"
    subtitle="Fixed promos have lower discount depth"
    yAxisTitle="Discount Rate"
    yFmt="pct2"
/>

## Campaign Timeline

<Alert status="info">
Campaign-level detail. High-revenue campaigns are not always high-discount — the most efficient promos 
combine modest discount depth with strong channel reach.
</Alert>

<DataTable data={promo_timeline} rows=10>
    <Column id=promo_name title="Promo"/>
    <Column id=promo_type title="Type"/>
    <Column id=start_date title="Start"/>
    <Column id=end_date title="End"/>
    <Column id=total_revenue title="Net Revenue" fmt=num0/>
    <Column id=total_discount title="Discount" fmt=num0/>
    <Column id=discount_rate title="Discount Rate" fmt=pct2/>
    <Column id=total_orders title="Orders" fmt=0/>
</DataTable>

## Top Revenue Campaigns

<Alert status="info">
The highest-revenue campaign is <b><Value data={top_promo} column=promo_name/></b> 
(<Value data={top_promo} column=promo_type/> via <Value data={top_promo} column=promo_channel/>),
generating <Value data={top_promo} column=total_revenue fmt=num0/> VND with a <Value data={top_promo} column=discount_rate fmt=pct2/> discount 
and <Value data={top_promo} column=roi fmt=0.0/>× ROI.
The top 10 campaigns reveal whether scale comes from discount depth or channel reach.
</Alert>

<DataTable data={promo_ranking} rows=10>
    <Column id=promo_name title="Promo"/>
    <Column id=promo_type title="Type"/>
    <Column id=promo_channel title="Channel"/>
    <Column id=total_revenue title="Net Revenue" fmt=num0/>
    <Column id=total_discount title="Discount" fmt=num0/>
    <Column id=discount_rate title="Discount Rate" fmt=pct2/>
    <Column id=total_orders title="Orders" fmt=0/>
    <Column id=roi title="ROI" fmt=0.0/>
</DataTable>

<Alert status="info">
<b>Category-restricted promotions</b> show different efficiency profiles than <b>site-wide</b> campaigns. 
Category promos typically have higher AOV but lower total scale — they attract buyers with existing category intent.
</Alert>

<Alert status="positive">
Action: Test category-specific campaigns for high-margin segments 
rather than always defaulting to site-wide percentage discounts.
</Alert>

<ScatterPlot
    data={category_scatter}
    x=discount_rate
    y=roi
    series=promo_type
    size=total_orders
    title="Category Promo Efficiency"
    subtitle="Discount depth vs ROI by category and promo type. Bubble size = order volume."
    xAxisTitle="Discount Rate"
    yAxisTitle="ROI"
    xFmt="pct2"
    yFmt="0.0"
>
    <ReferenceLine x=0.20 label="20% Threshold" hideValue=true color=warning lineType=dashed/>
</ScatterPlot>

<BarChart
    data={category_impact}
    x=category_scope
    y=avg_aov
    title="Average Order Value by Category Scope"
    subtitle="Category promos attract higher-intent buyers"
    yAxisTitle="AOV"
    yFmt="num0"
/>

## Discount Depth vs Revenue

<Alert status="warning">
Higher discount rates do not always yield higher revenue. The scatter reveals a "diminishing returns" zone 
where deep discounts (above 20%) fail to lift revenue proportionally — classic margin erosion without volume compensation.
</Alert>

<BubbleChart
    data={promo_vs_discount}
    x=discount_rate
    y=total_revenue
    series=promo_type
    size=total_orders
    title="Campaign Efficiency: Discount vs Revenue"
    subtitle="Bubble size = total orders. Top-left = efficient; bottom-right = margin destroyers"
    xAxisTitle="Discount Rate"
    yAxisTitle="Net Revenue"
    xFmt="pct2"
    yFmt="num0"
>
    <ReferenceArea xMin=0.20 label="Diminishing Returns" color=warning opacity=0.18/>
</BubbleChart>

<Alert status="info">
Average discount rate across all campaigns: <Value data={avg_discount} column=avg_discount fmt=pct2/>.
</Alert>

## Channel Breakdown

<Alert status="info">
Channel performance reveals where promotional dollars work hardest. 
Email and social typically have lower CAC; paid search and display require tighter ROI thresholds.
</Alert>

<BarChart
    data={channel_breakdown}
    x=promo_channel
    y=total_revenue
    title="Revenue by Promotion Channel"
    subtitle="Which channels drive the most promo-attributed revenue"
    yAxisTitle="Net Revenue"
    yFmt="num0"
/>

## Daily Discount Pressure

<Alert status="warning">
Heavy discounting erodes margin. Days with discount above 10% of revenue warrant investigation 
into whether the lift justifies the margin sacrifice. Sustained high-discount periods suggest weak organic demand.
</Alert>

<AreaChart
    data={daily_promo_pressure}
    x=sales_date
    y=total_discount_amount
    title="Daily Discount Amount Over Time"
    subtitle="Promotional spend trend"
    yAxisTitle="Discount Amount"
    xAxisTitle="Date"
    yFmt="num0"
/>

## Discount Pattern by Day of Week

<Alert status="info">
Discount intensity often follows traffic patterns — deeper discounts on low-conversion days (weekends) 
may be a misallocation. Shift promotional depth to Wednesday–Thursday when conversion is already highest.
</Alert>

<BarChart
    data={discount_heatmap_dow}
    x=day_name
    y=avg_discount
    title="Average Discount by Day of Week"
    subtitle="Identifies weekly promotional rhythm"
    yAxisTitle="Discount Amount"
    yFmt="num0"
/>

## Related Stories

- [Promo Paradox](/01-stories/marketing/02-promo-paradox)
- [Cannibalization Test](/01-stories/marketing/03-cannibalization-test)
- [05 Discount Calendar Ritual](/01-stories/marketing/05-discount-calendar-ritual)

