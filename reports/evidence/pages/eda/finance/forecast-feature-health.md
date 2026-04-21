---
title: Forecast Feature Health
---

# Forecast Feature Readiness

This page validates lag/rolling features before modeling runs.

```sql feature_nulls
select
    count(*) as total_rows,
    sum(case when lag_1d_revenue is null then 1 else 0 end) as null_lag_1d_revenue,
    sum(case when lag_7d_revenue is null then 1 else 0 end) as null_lag_7d_revenue,
    sum(case when lag_28d_revenue is null then 1 else 0 end) as null_lag_28d_revenue,
    sum(case when roll_mean_7d_revenue is null then 1 else 0 end) as null_roll_mean_7d_revenue,
    sum(case when lag_1d_sessions is null then 1 else 0 end) as null_lag_1d_sessions
from datathon_warehouse.mart_forecast_daily_modeling
```

```sql lag_view
select
    sales_date,
    revenue,
    lag_1d_revenue,
    lag_7d_revenue,
    lag_28d_revenue,
    roll_mean_7d_revenue,
    lag_1d_sessions,
    lag_1m_avg_stockout_days
from datathon_warehouse.mart_forecast_daily_modeling
order by sales_date
```

```sql revenue_lag7_long
select sales_date, 'Revenue' as metric, revenue as value
from datathon_warehouse.mart_forecast_daily_modeling
union all
select sales_date, 'Lag 7 Revenue' as metric, lag_7d_revenue as value
from datathon_warehouse.mart_forecast_daily_modeling
order by sales_date
```

<DataTable data={feature_nulls} rows=10 />

`null_*` values at the beginning of series are expected for lag windows.

<LineChart
    data={revenue_lag7_long}
    x=sales_date
    y=value
    series=metric
    yAxisTitle="Revenue"
    xAxisTitle="Date"
    title="Revenue and Lag-7 Baseline"
    subtitle="Visual sanity check for leakage-safe lag alignment"
    yFmt="num0"
/>

<DataTable data={lag_view} rows=10 />
