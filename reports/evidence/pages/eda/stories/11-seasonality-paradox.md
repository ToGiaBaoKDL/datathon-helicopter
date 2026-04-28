---
title: The Seasonality Paradox
---

# The Seasonality Paradox

<Alert status="warning">
<b>The question:</b> Q4 average seasonal index is <b><Value data={q4_avg} column=q4_index fmt=num2/></b>, Q1 is <b><Value data={q1_avg} column=q1_index fmt=num2/></b>.
April–May peaks at <b><Value data={peak_months} column=seasonal_index row=0 fmt=num2/></b>. Why does this business not benefit from year-end holidays?
</Alert>

```sql seasonal_index
select
    month,
    round(avg_revenue, 0) as avg_revenue,
    round(seasonal_index, 3) as seasonal_index
from datathon_warehouse.mart_seasonal_pattern
order by month
```

```sql q4_avg
select round(avg(seasonal_index), 3) as q4_index
from datathon_warehouse.mart_seasonal_pattern
where month in (10, 11, 12)
```

```sql q1_avg
select round(avg(seasonal_index), 3) as q1_index
from datathon_warehouse.mart_seasonal_pattern
where month in (1, 2, 3)
```

```sql peak_months
select
    month,
    seasonal_index
from datathon_warehouse.mart_seasonal_pattern
where seasonal_index > 1.4
order by seasonal_index desc
```

```sql monthly_revenue_trend
select
    date_trunc('month', sales_date) as month_start,
    sum(revenue) as monthly_revenue,
    sum(order_count) as monthly_orders
from datathon_warehouse.mart_forecast_daily_base
group by 1
order by 1
```

```sql day_of_week_pattern
select
    strftime(sales_date, '%a') as day_name,
    round(avg(revenue), 0) as avg_revenue,
    round(avg(order_count), 0) as avg_orders
from datathon_warehouse.mart_forecast_daily_base
group by 1
order by case day_name when 'Mon' then 1 when 'Tue' then 2 when 'Wed' then 3 when 'Thu' then 4 when 'Fri' then 5 when 'Sat' then 6 when 'Sun' then 7 end
```

```sql month_end_effect
select
    case
        when dayofmonth(sales_date) > 28 then 'Month-End (29-31)'
        else 'Other Days'
    end as period,
    round(avg(revenue), 0) as avg_revenue
from datathon_warehouse.mart_forecast_daily_base
group by 1
```

## 1. The Pattern: April–May Peak, Q4 Trough

<Alert status="info">
The seasonal index reveals a counter-intuitive pattern. 
Q4 (Oct–Dec) averages <b><Value data={q4_avg} column=q4_index fmt=num2/></b> — well below baseline. 
Q1 (Jan–Mar) averages <b><Value data={q1_avg} column=q1_index fmt=num2/></b>. 
The peak is <b>April–May</b> at <Value data={peak_months} column=seasonal_index row=0 fmt=num2/> — not year-end.
</Alert>

<AreaChart
    data={seasonal_index}
    x=month
    y=seasonal_index
    title="Seasonal Index by Month"
    subtitle="Index = 1.0 is annual average. Peak = Apr–May, Trough = Nov–Dec"
    yAxisTitle="Seasonal Index"
    yFmt="0.00"
>
    <ReferenceLine y=1.0 label="Baseline" hideValue=true color=neutral/>
    <ReferenceArea xMin=4 xMax=6 label="Peak" color=positive/>
    <ReferenceArea xMin=10 xMax=12 label="Trough" color=negative/>
</AreaChart>

## 2. Reality Check: Actual Monthly Revenue

<Alert status="info">
The seasonal index is not a model — it is derived from actual revenue. 
The chart below confirms the pattern: April–May peaks are real, and Q4 is consistently weak.
</Alert>

<AreaChart
    data={monthly_revenue_trend}
    x=month_start
    y=monthly_revenue
    title="Actual Monthly Revenue Trend"
    subtitle="Confirms Apr–May peak and Q4 weakness in raw data"
    yAxisTitle="Revenue (VND)"
    yFmt="num0"
/>

## 3. Day-of-Week: Weekend Weakness

<Alert status="info">
Weekdays outperform weekends — this is a B2C or salary-cycle business. 
Orders cluster around mid-week and month-end paycheck timing.
</Alert>

<BarChart
    data={day_of_week_pattern}
    x=day_name
    y=avg_revenue
    title="Average Revenue by Day of Week"
    subtitle="Salary-cycle pattern: weekdays outperform weekends"
    yAxisTitle="Revenue (VND)"
    yFmt="num0"
/>

## 4. Month-End Effect: Paycheck Spike

<Alert status="info">
Month-end days (29–31) generate substantially more revenue than other days. 
This confirms the salary-cycle hypothesis — customers shop when they get paid.
</Alert>

<BarChart
    data={month_end_effect}
    x=period
    y=avg_revenue
    title="Month-End vs Other Days"
    subtitle="Paycheck effect: month-end days outperform"
    yAxisTitle="Revenue (VND)"
    yFmt="num0"
/>

## The Verdict

<Alert status="positive">
<b>Action:</b> This business peaks in <b>April–May</b> (salary cycle + seasonal demand) and troughs in <b>November–December</b>. 
The conventional Q4 holiday marketing playbook is wrong for this category. 
Shift marketing budget from Q4 to Apr–May. Run month-end flash sales to capture paycheck timing.
</Alert>
