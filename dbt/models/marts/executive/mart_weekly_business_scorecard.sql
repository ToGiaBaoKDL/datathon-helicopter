with daily_base as (
    select
        sales_date,
        revenue,
        cogs,
        order_count,
        sessions,
        return_units,
        total_discount_amount,
        cancelled_line_count
    from {{ ref('mart_forecast_daily_base') }}
),
weekly as (
    select
        date_trunc('week', sales_date) as week_start_date,
        sum(revenue) as revenue,
        sum(cogs) as cogs,
        sum(order_count) as order_count,
        sum(sessions) as sessions,
        sum(return_units) as return_units,
        sum(total_discount_amount) as total_discount_amount,
        sum(cancelled_line_count) as cancelled_line_count
    from daily_base
    group by 1
)

select
    week_start_date,
    revenue,
    cogs,
    revenue - cogs as gross_profit,
    cast(revenue - cogs as double) / nullif(revenue, 0) as gross_margin_rate,
    order_count,
    sessions,
    cast(order_count as double) / nullif(sessions, 0) as session_to_order_rate,
    return_units,
    total_discount_amount,
    cancelled_line_count,
    lag(revenue, 1) over (order by week_start_date) as prev_week_revenue,
    cast(revenue as double)
        / nullif(lag(revenue, 1) over (order by week_start_date), 0) - 1
        as wow_revenue_growth_rate,
    lag(order_count, 1) over (order by week_start_date) as prev_week_order_count,
    cast(order_count as double)
        / nullif(lag(order_count, 1) over (order by week_start_date), 0) - 1
        as wow_order_growth_rate
from weekly
