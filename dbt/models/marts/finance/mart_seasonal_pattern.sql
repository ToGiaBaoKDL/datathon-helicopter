-- Seasonal revenue pattern and index for predictive analysis.
-- Grain: month (1-12) aggregated across all years.

with monthly_revenue as (
    select
        date_trunc('month', sales_date) as month_start,
        date_part('year', sales_date) as year,
        sum(revenue) as monthly_revenue
    from {{ ref('mart_forecast_daily_base') }}
    group by 1, 2
),

monthly_avg as (
    select
        month_start,
        avg(monthly_revenue) as avg_monthly_revenue
    from monthly_revenue
    group by 1
),

overall_avg as (
    select avg(avg_monthly_revenue) as overall_avg_revenue from monthly_avg
)

select
    date_part('month', ma.month_start) as month,
    avg(ma.avg_monthly_revenue) as avg_revenue,
    oa.overall_avg_revenue,
    cast(avg(ma.avg_monthly_revenue) as double) / nullif(oa.overall_avg_revenue, 0)
        as seasonal_index,
    avg(ma.avg_monthly_revenue) - oa.overall_avg_revenue as revenue_deviation
from monthly_avg as ma
    cross join overall_avg as oa
group by 1, oa.overall_avg_revenue
order by 1
