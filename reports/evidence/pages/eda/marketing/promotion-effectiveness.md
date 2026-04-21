---
title: Promotion Effectiveness
---

# Promotion Effectiveness

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
    avg(avg_order_value) as avg_aov
from datathon_warehouse.mart_promotion_effectiveness
where promo_type in ${inputs.type_filter.value}
  and promo_channel in ${inputs.channel_filter.value}
group by 1
order by total_revenue desc
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

## Promo Type Summary

<BarChart
    data={promo_summary}
    x=promo_type
    y=total_revenue
    title="Revenue by Promotion Type"
    subtitle="Percentage vs fixed discount campaigns"
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
    yFmt="0.0%"
/>

## Campaign Timeline

<DataTable data={promo_timeline} rows=10 />

## Discount Depth vs Revenue

<ScatterPlot
    data={promo_vs_discount}
    x=discount_rate
    y=total_revenue
    size=total_orders
    title="Discount Rate vs Campaign Revenue"
    subtitle="Bubble size = total orders"
    xAxisTitle="Discount Rate"
    yAxisTitle="Net Revenue"
    xFmt="0.0%"
    yFmt="num0"
>
    <ReferenceLine data={avg_discount} x=avg_discount label="Avg Discount" hideValue=true color=info/>
</ScatterPlot>

## Channel Breakdown

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

<BarChart
    data={discount_heatmap_dow}
    x=day_name
    y=avg_discount
    title="Average Discount by Day of Week"
    subtitle="Identifies weekly promotional rhythm"
    yAxisTitle="Discount Amount"
    yFmt="num0"
/>
