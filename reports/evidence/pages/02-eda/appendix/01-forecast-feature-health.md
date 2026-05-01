---
title: Forecast Feature Health
---

This page validates lag/rolling features before modeling runs.

```sql feature_nulls
select
    count(*) as total_rows,
    sum(case when lag_1d_revenue is null then 1 else 0 end) as null_lag_1d_revenue,
    sum(case when lag_7d_revenue is null then 1 else 0 end) as null_lag_7d_revenue,
    sum(case when lag_28d_revenue is null then 1 else 0 end) as null_lag_28d_revenue,
    sum(case when roll_mean_7d_revenue is null then 1 else 0 end) as null_roll_mean_7d_revenue,
    sum(case when lag_1d_cogs is null then 1 else 0 end) as null_lag_1d_cogs
from datathon_warehouse.mart_forecast_daily_features
```

```sql lag_view
select
    sales_date,
    revenue,
    lag_1d_revenue,
    lag_7d_revenue,
    lag_28d_revenue,
    roll_mean_7d_revenue,
    lag_1d_cogs,
    lag_365d_revenue
from datathon_warehouse.mart_forecast_daily_features
order by sales_date
```

```sql revenue_lag7_long
select sales_date, 'Revenue' as metric, revenue as value
from datathon_warehouse.mart_forecast_daily_features
union all
select sales_date, 'Lag 7 Revenue' as metric, lag_7d_revenue as value
from datathon_warehouse.mart_forecast_daily_features
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

```sql baseline_compare
select
    sales_date,
    revenue,
    revenue_baseline,
    lag_1d_revenue,
    revenue - revenue_baseline as revenue_residual
from datathon_warehouse.mart_forecast_daily_features
order by sales_date
```

```sql revenue_baseline_long
select sales_date, 'Revenue (Actual)' as metric, revenue as value
from datathon_warehouse.mart_forecast_daily_features
union all
select sales_date, 'Revenue Baseline' as metric, revenue_baseline as value
from datathon_warehouse.mart_forecast_daily_features
union all
select sales_date, 'Naive (Lag 1d)' as metric, lag_1d_revenue as value
from datathon_warehouse.mart_forecast_daily_features
order by sales_date
```

<LineChart
    data={revenue_baseline_long}
    x=sales_date
    y=value
    series=metric
    yAxisTitle="Revenue"
    xAxisTitle="Date"
    title="Actual Revenue vs Baseline Predictions"
    subtitle="Baseline = additive seasonal decomposition (dow + month - overall) from SQL mart"
    yFmt="num0"
/>

```sql residual_stats
select
    avg(abs(revenue - revenue_baseline))::int as mae_baseline,
    avg(abs(revenue - lag_1d_revenue))::int as mae_naive_1d,
    avg(abs(revenue - lag_7d_revenue))::int as mae_naive_7d,
    avg(abs(revenue - lag_365d_revenue))::int as mae_naive_365d,
    round(avg((revenue - revenue_baseline) / nullif(revenue, 0)) * 100, 2) as avg_pct_error_baseline
from datathon_warehouse.mart_forecast_daily_features
where lag_1d_revenue is not null
```

<DataTable data={residual_stats} rows=10 />

<DataTable data={lag_view} rows=10 />
