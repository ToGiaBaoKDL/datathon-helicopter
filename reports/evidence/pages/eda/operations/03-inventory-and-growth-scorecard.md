---
title: Inventory and Growth Scorecard
---

This page monitors supply health and links it to growth trajectory.

```sql _date_bounds
select sales_date from datathon_warehouse.mart_monthly_inventory_snapshot
```

```sql stockout_overstock_overlap
select count(*) as overlap_count
from datathon_warehouse.mart_monthly_product_health
where stockout_flag = 1 and overstock_flag = 1
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
where sales_date >= date_trunc('month', cast('${inputs.date_range.start}' as date))
  and sales_date <= cast('${inputs.date_range.end}' as date)
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
where week_start_date >= date_trunc('week', cast('${inputs.date_range.start}' as date))
  and week_start_date <= date_trunc('week', cast('${inputs.date_range.end}' as date))
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
    max(avg_stockout_days) as avg_stockout_days
from datathon_warehouse.mart_monthly_inventory_snapshot
where sales_date >= date_trunc('month', cast('${inputs.date_range.start}' as date))
  and sales_date <= cast('${inputs.date_range.end}' as date)
group by 1, 2
order by 1, 2
```

```sql engagement_daily
select
    sales_date,
    bounce_rate,
    pages_per_session,
    avg_session_duration_sec
from datathon_warehouse.mart_daily_marketing_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
order by sales_date
```

```sql inventory_kpis
select
    avg(avg_days_of_supply) as avg_days_supply,
    avg(avg_fill_rate) as avg_fill_rate,
    avg(avg_sell_through_rate) as avg_sell_through,
    avg(stockout_product_count) as avg_stockout_products,
    avg(overstock_product_count) as avg_overstock_products
from datathon_warehouse.mart_monthly_inventory_snapshot
where sales_date >= date_trunc('month', cast('${inputs.date_range.start}' as date))
  and sales_date <= cast('${inputs.date_range.end}' as date)
```

```sql conversion_lift
select
    avg(session_to_order_rate) as current_conversion,
    (avg(session_to_order_rate) + 0.01) / nullif(avg(session_to_order_rate), 0) - 1 as lift_pct
from datathon_warehouse.mart_daily_marketing_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
  and sessions > 0
```

## Inventory Health Overview

<Alert status="warning">
The business carries <b><Value data={inventory_kpis} column=avg_days_supply fmt=0/> days of supply</b> on average — multiple years of inventory. 
With a sell-through rate of only <Value data={inventory_kpis} column=avg_sell_through fmt=pct2/>, working capital is severely tied up in slow-moving stock. 
This is a bigger problem than stockouts.
</Alert>

<Alert status="positive">
Action: Target 90 days of supply (industry standard). A reduction to 90 days would free 
~90% of inventory capital for reinvestment in marketing or product development.
</Alert>

<Grid cols=4>
    <BigValue
        data={inventory_kpis}
        value=avg_days_supply
        title="Days of Supply"
        fmt="0"
    />
    <BigValue
        data={inventory_kpis}
        value=avg_fill_rate
        title="Fill Rate"
        fmt="pct2"
    />
    <BigValue
        data={inventory_kpis}
        value=avg_sell_through
        title="Sell-Through Rate"
        fmt="pct2"
    />
    <BigValue
        data={inventory_kpis}
        value=avg_stockout_products
        title="Stockout Products"
        fmt="0"
    />
</Grid>

## Inventory Stockout Pressure

<Alert status="info">
Stockout days have improved gradually over the decade — inventory availability is getting better, not worse. 
This rules out stockouts as the primary cause of revenue decline.
</Alert>

<Alert status="warning">
<Value data={stockout_overstock_overlap} column=overlap_count fmt=num0/> product-months have both stockout_flag = 1 and overstock_flag = 1 in raw data. 
This suggests data quality issues in inventory classification, not necessarily operational paradox.
</Alert>

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

<Alert status="info">
Revenue growth and order growth generally move together — when they diverge, it signals AOV or mix shifts. 
Watch for revenue growth lagging order growth (discounting pressure) or outpacing it (premium mix shift).
</Alert>

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
    yFmt="pct2"
    y2Fmt="pct2"
>
    <ReferenceLine y=0 label="Zero Growth" hideValue=true color=info/>
</BarChart>

## Engagement Quality Trend

<Alert status="info">
Bounce rate is suspiciously low for e-commerce — typical is 20–50%. Pages per session is healthy. 
If bounce rate is measured as "single-page sessions / all sessions", the reported figure suggests 
almost all visitors browse multiple pages. This is either exceptional engagement or a measurement definition issue.
</Alert>

<LineChart
    data={engagement_daily}
    x=sales_date
    y=bounce_rate
    title="Daily Bounce Rate"
    subtitle="Share of sessions viewing only one page"
    yAxisTitle="Bounce Rate"
    yFmt="pct2"
>
    <ReferenceLine y=0.20 label="20% Benchmark" hideValue=true color=info/>
</LineChart>

<LineChart
    data={engagement_daily}
    x=sales_date
    y=pages_per_session
    title="Pages per Session"
    subtitle="Average page views per visitor session"
    yAxisTitle="Pages"
    yFmt="0.0"
/>

## Conversion Trend

<Alert status="warning">
Session-to-order rate has collapsed by roughly three-quarters since 2013. 
This is the dominant driver of revenue pressure. Traffic is flat; capture is broken.
</Alert>

<Alert status="positive">
Action: Audit checkout flow, page load speed, mobile UX, and payment coverage. 
A +1pp conversion lift would project <Value data={conversion_lift} column=lift_pct fmt=pct2/> incremental revenue.
</Alert>

<LineChart
    data={traffic_conversion_daily}
    x=sales_date
    y=session_to_order_rate
    title="Session to Order Conversion"
    subtitle="Daily demand capture efficiency"
    yAxisTitle="Conversion Rate"
    xAxisTitle="Date"
    yFmt="pct2"
>
    <ReferenceLine y=0.012 label="2013 Peak" hideValue=true color=positive lineType=dashed/>
    <ReferenceLine y=0.003 label="2022 Low" hideValue=true color=negative lineType=dashed/>
</LineChart>

## Conversion by Day of Week

<Alert status="info">
Wednesday consistently shows the highest conversion rate, while Saturday is the weakest. 
This contradicts the common weekend-peak assumption and has direct ad-spend implications.
</Alert>

<BarChart
    data={conversion_heatmap_dow}
    x=day_name
    y=avg_conversion_rate
    title="Conversion Rate by Day of Week"
    subtitle="Weekly rhythm of traffic-to-order capture"
    yAxisTitle="Conversion Rate"
    yFmt="pct2"
>
    <ReferenceLine y=0.005 label="0.5% Target" hideValue=true color=positive lineType=dashed/>
</BarChart>

## Seasonal Stockout Pattern

<Alert status="info">
Monthly stockout patterns reveal seasonal inventory stress. Higher stockout days in certain months 
may indicate inadequate forward buying before demand peaks.
</Alert>

<Alert status="positive">
Action: If stockout days spike consistently before Q4 (holiday season), increase safety stock 
by 20–30% in September to cover October–November demand surge.
</Alert>

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

## Weekly Detail

<DataTable data={weekly_scorecard} rows=10>
    <Column id=week_start_date title="Week"/>
    <Column id=revenue title="Revenue" fmt=num0/>
    <Column id=cogs title="COGS" fmt=num0/>
    <Column id=gross_profit title="Gross Profit" fmt=num0/>
    <Column id=gross_margin_rate title="Margin" fmt=pct2/>
    <Column id=order_count title="Orders" fmt=0/>
    <Column id=sessions title="Sessions" fmt=0/>
    <Column id=session_to_order_rate title="Conversion" fmt=pct2/>
    <Column id=wow_revenue_growth_rate title="Revenue WoW" fmt=pct2/>
    <Column id=wow_order_growth_rate title="Order WoW" fmt=pct2/>
</DataTable>

## Inventory Detail

<DataTable data={inventory_daily} rows=10>
    <Column id=sales_date title="Date"/>
    <Column id=stock_on_hand_total title="Stock on Hand" fmt=0/>
    <Column id=units_received_total title="Received" fmt=0/>
    <Column id=units_sold_total title="Sold" fmt=0/>
    <Column id=avg_stockout_days title="Stockout Days" fmt=0.00/>
    <Column id=avg_days_of_supply title="Days Supply" fmt=0/>
    <Column id=avg_fill_rate title="Fill Rate" fmt=pct2/>
    <Column id=avg_sell_through_rate title="Sell-Through" fmt=pct2/>
    <Column id=stockout_product_count title="Stockout SKUs" fmt=0/>
    <Column id=overstock_product_count title="Overstock SKUs" fmt=0/>
</DataTable>

## Related Stories

- [Inventory Capital Trap](/stories/product/01-inventory-capital-trap)

