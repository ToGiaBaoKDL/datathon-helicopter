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

<LineChart
    data={fulfillment_daily}
    x=sales_date
    y=avg_days_to_deliver
    title="Average Days to Deliver"
    subtitle="End-to-end delivery speed trend"
    yAxisTitle="Days"
    xAxisTitle="Date"
    yFmt="0"
/>

<LineChart
    data={returns_daily}
    x=sales_date
    y=return_record_rate
    title="Daily Return Record Rate"
    subtitle="Share of order lines with a return record"
    yAxisTitle="Return Rate"
    xAxisTitle="Date"
    yFmt="0.0%"
>
    <ReferenceLine y=0.05 label="5% Threshold" hideValue=true color=negative/>
</LineChart>

<LineChart
    data={returns_daily}
    x=sales_date
    y=return_unit_rate
    title="Daily Return Unit Rate"
    subtitle="Share of sold units that are returned"
    yAxisTitle="Return Rate"
    xAxisTitle="Date"
    yFmt="0.0%"
>
    <ReferenceLine y=0.05 label="5% Threshold" hideValue=true color=negative/>
</LineChart>

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
    data={returns_heatmap_dow}
    x=day_name
    y=avg_return_rate
    title="Average Return Rate by Day of Week"
    subtitle="Pinpoints weekly return friction clusters"
    yAxisTitle="Return Rate"
    yFmt="0.0%"
/>

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

<DataTable data={fulfillment_daily} rows=10/>
<DataTable data={returns_daily} rows=10/>
