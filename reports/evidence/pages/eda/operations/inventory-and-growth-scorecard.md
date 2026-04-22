---
title: Inventory and Growth Scorecard
---

# Inventory and Growth Scorecard

This page monitors supply health and links it to growth trajectory.

```sql _date_bounds
select sales_date from datathon_warehouse.mart_monthly_inventory_snapshot
```

<DateRange name=date_range data={_date_bounds} dates=sales_date/>

```sql inventory_daily
select
    sales_date,
    stock_on_hand_total,
    units_received_total,
    units_sold_total,
    avg_stockout_days,
    avg_days_of_supply,
    avg_fill_rate,
    avg_sell_through_rate,
    stockout_product_count,
    overstock_product_count,
    reorder_product_count
from datathon_warehouse.mart_monthly_inventory_snapshot
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
order by sales_date
```

```sql weekly_scorecard
select
    week_start_date,
    revenue,
    cogs,
    gross_profit,
    gross_margin_rate,
    order_count,
    sessions,
    session_to_order_rate,
    wow_revenue_growth_rate,
    wow_order_growth_rate,
    return_units,
    total_discount_amount,
    cancelled_line_count
from datathon_warehouse.mart_weekly_business_scorecard
where week_start_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
order by week_start_date
```

```sql traffic_conversion_daily
select
    sales_date,
    sessions,
    order_count,
    session_to_order_rate,
    pages_per_session,
    bounce_rate
from datathon_warehouse.mart_daily_marketing_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
order by sales_date
```

```sql conversion_heatmap_dow
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
    avg(session_to_order_rate) as avg_conversion_rate
from datathon_warehouse.mart_daily_marketing_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
  and sessions > 0
group by 1, 2
order by 1
```

```sql monthly_stockout_heatmap
select
    extract(year from sales_date) as year,
    extract(month from sales_date) as month,
    avg(avg_stockout_days) as avg_stockout_days
from datathon_warehouse.mart_monthly_inventory_snapshot
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
group by 1, 2
order by 1, 2
```

<LineChart
    data={inventory_daily}
    x=sales_date
    y=avg_stockout_days
    title="Inventory Stockout Pressure"
    subtitle="Days products are out of stock on average"
    yAxisTitle="Avg Stockout Days"
    xAxisTitle="Date"
    yFmt="0"
/>

## Weekly Growth: Revenue vs Orders

<BarChart
    data={weekly_scorecard}
    x=week_start_date
    y=wow_revenue_growth_rate
    y2=wow_order_growth_rate
    y2SeriesType=line
    title="Weekly Growth: Revenue vs Orders"
    subtitle="Bar = revenue growth, Line = order growth"
    yAxisTitle="Revenue Growth"
    y2AxisTitle="Order Growth"
    yFmt="0.0%"
    y2Fmt="0.0%"
/>

<LineChart
    data={traffic_conversion_daily}
    x=sales_date
    y=session_to_order_rate
    title="Session to Order Conversion"
    subtitle="Daily demand capture efficiency"
    yAxisTitle="Conversion Rate"
    xAxisTitle="Date"
    yFmt="0.0%"
/>

<BarChart
    data={conversion_heatmap_dow}
    x=day_name
    y=avg_conversion_rate
    title="Conversion Rate by Day of Week"
    subtitle="Weekly rhythm of traffic-to-order capture"
    yAxisTitle="Conversion Rate"
    yFmt="0.0%"
/>

<BarChart
    data={monthly_stockout_heatmap}
    x=month
    y=avg_stockout_days
    series=year
    title="Monthly Stockout Days by Year"
    subtitle="Seasonal inventory availability pattern"
    yAxisTitle="Stockout Days"
    yFmt="0.00"
/>

<DataTable data={weekly_scorecard} rows=10/>
<DataTable data={inventory_daily} rows=10/>
