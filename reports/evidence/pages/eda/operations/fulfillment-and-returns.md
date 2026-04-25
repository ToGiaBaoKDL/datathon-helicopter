---
title: Fulfillment and Returns
---

# Fulfillment and Returns

This page tracks delivery reliability and return friction to protect customer experience.

```sql _date_bounds
select sales_date from datathon_warehouse.mart_daily_returns_kpis
```

<DateRange name=date_range data={_date_bounds} dates=sales_date/>

```sql fulfillment_daily
select
    sales_date,
    shipped_order_count,
    avg_days_to_ship,
    avg_days_in_transit,
    avg_days_to_deliver,
    free_shipping_share,
    avg_shipping_fee
from datathon_warehouse.mart_daily_fulfillment_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
order by sales_date
```

```sql returns_daily
select
    sales_date,
    return_record_rate,
    return_unit_rate,
    refund_amount,
    defective_return_count,
    wrong_size_return_count,
    late_delivery_return_count
from datathon_warehouse.mart_daily_returns_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
order by sales_date
```

```sql latest_fulfillment
select
    free_shipping_share,
    avg_shipping_fee
from datathon_warehouse.mart_daily_fulfillment_kpis
where sales_date <= '${inputs.date_range.end}'
order by sales_date desc
limit 1
```

```sql returns_long
select sales_date, 'Return Record Rate' as metric, return_record_rate as value
from datathon_warehouse.mart_daily_returns_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
union all
select sales_date, 'Return Unit Rate' as metric, return_unit_rate as value
from datathon_warehouse.mart_daily_returns_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
order by sales_date, metric
```

```sql returns_reason_summary
select
    'defective' as return_reason,
    sum(defective_return_count) as reason_count
from datathon_warehouse.mart_daily_returns_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
union all
select
    'wrong_size' as return_reason,
    sum(wrong_size_return_count) as reason_count
from datathon_warehouse.mart_daily_returns_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
union all
select
    'changed_mind' as return_reason,
    sum(changed_mind_return_count) as reason_count
from datathon_warehouse.mart_daily_returns_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
union all
select
    'not_as_described' as return_reason,
    sum(not_as_described_return_count) as reason_count
from datathon_warehouse.mart_daily_returns_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
union all
select
    'late_delivery' as return_reason,
    sum(late_delivery_return_count) as reason_count
from datathon_warehouse.mart_daily_returns_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
```

```sql returns_reason_pct
select
    return_reason,
    reason_count,
    reason_count::double / sum(reason_count) over () as reason_pct
from ${returns_reason_summary}
order by reason_count desc
```

```sql top_return_reason
select return_reason, reason_count, reason_pct
from ${returns_reason_pct}
order by reason_count desc
limit 1
```

```sql returns_heatmap_dow
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
    avg(return_record_rate) as avg_return_rate
from datathon_warehouse.mart_daily_returns_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
group by 1, 2
order by 1
```

```sql monthly_return_heatmap
select
    extract(year from sales_date) as year,
    extract(month from sales_date) as month,
    avg(return_record_rate) as avg_return_rate
from datathon_warehouse.mart_daily_returns_kpis
where sales_date between '${inputs.date_range.start}' and '${inputs.date_range.end}'
group by 1, 2
order by 1, 2
```

## Delivery Performance

<Alert status="info">
Delivery time has remained remarkably stable across the entire dataset. 
This is a strength — unlike conversion or revenue, fulfillment reliability has not degraded over time.
</Alert>

<Alert status="warning">
Only <Value data={latest_fulfillment} column=free_shipping_share fmt=pct1/> of orders have free shipping. In e-commerce, free shipping is one of the highest-ROI conversion tactics. 
With average shipping fee at only <Value data={latest_fulfillment} column=avg_shipping_fee fmt=num0/> VND (effectively free already), the business should test 
"free shipping on all orders" messaging to remove the psychological barrier.
</Alert>

<Grid cols=3>
    <BigValue
        data={fulfillment_daily}
        value=avg_days_to_deliver
        title="Days to Deliver"
        fmt="0.0"
    />
    <BigValue
        data={fulfillment_daily}
        value=avg_days_to_ship
        title="Days to Ship"
        fmt="0.0"
    />
    <BigValue
        data={fulfillment_daily}
        value=avg_days_in_transit
        title="Days in Transit"
        fmt="0.0"
    />
</Grid>

<LineChart
    data={fulfillment_daily}
    x=sales_date
    y=avg_days_to_deliver
    title="Average Days to Deliver"
    subtitle="End-to-end delivery speed trend"
    yAxisTitle="Days"
    xAxisTitle="Date"
    yFmt="0"
>
    <ReferenceLine y=7 label="7-Day SLA" hideValue=true color=warning/>
</LineChart>

## Return Rate Trends

<Alert status="warning">
Return rates fluctuate around the 5% quality threshold but periodically spike above it. 
Sustained elevation indicates root-cause issues in product quality, sizing accuracy, or fulfillment damage.
</Alert>

<Alert status="positive">
Action: Focus on controllable return reasons — "defective" and "wrong_size" are fixable with supplier QC and sizing guides. 
"Changed_mind" is behavioral and harder to influence.
</Alert>

<LineChart
    data={returns_long}
    x=sales_date
    y=value
    series=metric
    title="Daily Return Rates"
    subtitle="Record rate (lines) vs Unit rate (units) — divergence signals batch defects"
    yAxisTitle="Return Rate"
    xAxisTitle="Date"
    yFmt="0.0%"
>
    <ReferenceLine y=0.05 label="5% Threshold" hideValue=true color=negative/>
</LineChart>

## Return Root Causes

<Alert status="info">
Understanding why customers return is the first step to reducing return volume. 
Defective and wrong-size returns are operational failures; changed-mind returns are market signals.
</Alert>

<Alert status="warning">
<b><Value data={top_return_reason} column=return_reason/></b> is the dominant return reason (<Value data={top_return_reason} column=reason_count fmt=num0/> returns, <Value data={top_return_reason} column=reason_pct fmt=pct1/> of total). 
This is a controllable operational failure — fixable with supplier QC and sizing guides.
</Alert>

<BarChart
    data={returns_reason_summary}
    x=return_reason
    y=reason_count
    title="Top Return Reasons"
    subtitle="Aggregated return volume by root cause"
    yAxisTitle="Return Count"
    yFmt="num0"
/>

<BarChart
    data={returns_reason_pct}
    x=return_reason
    y=reason_pct
    title="Return Reason Share"
    subtitle="Percentage of total returns by root cause"
    yAxisTitle="Share of Returns"
    yFmt="0.0%"
/>

## Return Patterns

<Alert status="info">
Return rates show both weekly and seasonal rhythms. Identifying high-risk days/months enables 
proactive quality checks before dispatch.
</Alert>

<BarChart
    data={returns_heatmap_dow}
    x=day_name
    y=avg_return_rate
    title="Average Return Rate by Day of Week"
    subtitle="Pinpoints weekly return friction clusters"
    yAxisTitle="Return Rate"
    yFmt="0.0%"
>
    <ReferenceLine y=0.05 label="5% Threshold" hideValue=true color=negative/>
</BarChart>

<BarChart
    data={monthly_return_heatmap}
    x=month
    y=avg_return_rate
    series=year
    title="Monthly Return Rate by Year"
    subtitle="Seasonal return quality pattern"
    yAxisTitle="Return Rate"
    yFmt="0.0%"
/>

## Daily Detail

<DataTable data={fulfillment_daily} rows=10/>
<DataTable data={returns_daily} rows=10/>
