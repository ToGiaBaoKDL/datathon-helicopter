---
title: The Seasonality Paradox
---

<Alert status="warning">
<b>The question:</b> Q4 average seasonal index is <b><Value data={q4_avg} column=q4_index fmt=num2/></b>, Q1 is <b><Value data={q1_avg} column=q1_index fmt=num2/></b>.
Spring peaks at <b><Value data={peak_months} column=seasonal_index row=0 fmt=num2/></b>. Why does this business not benefit from year-end holidays?
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

```sql daily_revenue_calendar
select
    sales_date,
    revenue
from datathon_warehouse.mart_forecast_daily_base
order by sales_date
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

```sql what_if_budget_shift
with annual as (
    select sum(revenue) as annual_revenue
    from datathon_warehouse.mart_forecast_daily_base
),
q4 as (
    select sum(revenue) as q4_revenue
    from datathon_warehouse.mart_forecast_daily_base
    where date_part('month', sales_date) in (10, 11, 12)
),
peak as (
    select sum(revenue) as peak_revenue
    from datathon_warehouse.mart_forecast_daily_base
    where date_part('month', sales_date) in (4, 5)
)
select
    a.annual_revenue,
    q.q4_revenue,
    p.peak_revenue,
    round(q.q4_revenue * 0.20, 0) as shifted_budget,
    round(p.peak_revenue / nullif(q.q4_revenue, 0), 2) as peak_to_q4_ratio,
    round(shifted_budget * (peak_to_q4_ratio - 1), 0) as projected_lift
from annual a, q4 q, peak p
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

<Alert status="info">
The calendar heatmap below reveals daily revenue intensity across the full period.
Bright clusters in Apr–May confirm the spring peak; dark stretches in Nov–Dec confirm the Q4 trough.
</Alert>

<CalendarHeatmap
    data={daily_revenue_calendar}
    date=sales_date
    value=revenue
    title="Daily Revenue Calendar"
    subtitle="Revenue intensity by day — spring shines, Q4 dims"
    valueFmt="num0"
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
    subtitle="Weekdays outperform weekends — consistent with a salary-cycle hypothesis"
    yAxisTitle="Revenue (VND)"
    yFmt="num0"
/>

## 4. What-If: Shift 20% of Q4 Budget to Apr–May

<Alert status="info">
Q4 revenue is <b><Value data={what_if_budget_shift} column=q4_revenue fmt=num0/></b> VND annually.
Apr–May revenue is <b><Value data={what_if_budget_shift} column=peak_revenue fmt=num0/></b> VND — 
<Value data={what_if_budget_shift} column=peak_to_q4_ratio fmt=0.00/>× the Q4 level.
If 20% of Q4 marketing budget (<Value data={what_if_budget_shift} column=shifted_budget fmt=num0/> VND equivalent) 
were reallocated to Apr–May where the seasonal index is higher,
projected revenue lift is <b><Value data={what_if_budget_shift} column=projected_lift fmt=num0/></b> VND annually.
<b>Caveat:</b> This assumes each marketing VND delivers the same return in peak months as in trough months.
In reality, peak-month competition may raise CAC, so the true lift is likely lower — treat this as an upper bound.
</Alert>

<Grid cols=3>
    <BigValue
        data={what_if_budget_shift}
        value=q4_revenue
        title="Q4 Annual Revenue"
        fmt="num0"
    />
    <BigValue
        data={what_if_budget_shift}
        value=peak_revenue
        title="Apr–May Annual Revenue"
        fmt="num0"
    />
    <BigValue
        data={what_if_budget_shift}
        value=projected_lift
        title="Projected Annual Lift"
        fmt="num0"
    />
</Grid>

## 5. Month-End Effect: Paycheck Spike

<Alert status="info">
Month-end days (29–31) generate substantially more revenue than other days. 
This pattern is consistent with a salary-cycle hypothesis — customers may shop when they receive income.
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
<b>Action:</b> This business peaks in <b>spring</b> (salary cycle + seasonal demand) and troughs in <b>Q4</b>. 
The conventional Q4 holiday marketing playbook is wrong for this category. 
Shift marketing budget from Q4 to Apr–May. Run month-end flash sales to capture paycheck timing.
</Alert>

## Deep Dive

- [Seasonal Decomposition](/eda/finance/03-seasonal-decomposition)

