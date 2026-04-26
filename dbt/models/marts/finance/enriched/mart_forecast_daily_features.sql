with base as (
    select
        sales_date,
        revenue,
        cogs,
        year,
        day_of_week,
        date_part('day', sales_date) as day_of_month,
        date_part('dayofyear', sales_date) as day_of_year,
        date_part('week', sales_date) as week_of_year,
        datediff('day', sales_date, date_trunc('month', sales_date) + interval '1 month')
            as days_to_month_end,
        datediff(
            'day',
            sales_date,
            date_trunc('quarter', sales_date) + interval '3 months' - interval '1 day'
        ) as days_to_quarter_end,
        case when date_part('day', sales_date) <= 3 then 1 else 0 end as is_month_start,
        sin(2 * pi() * date_part('month', sales_date) / 12) as month_sin,
        cos(2 * pi() * date_part('month', sales_date) / 12) as month_cos,
        sin(2 * pi() * day_of_week / 7) as day_of_week_sin,
        cos(2 * pi() * day_of_week / 7) as day_of_week_cos,
        sin(2 * pi() * day_of_year / case when year % 4 = 0 and (year % 100 != 0 or year % 400 = 0) then 366 else 365 end) as day_of_year_sin,
        cos(2 * pi() * day_of_year / case when year % 4 = 0 and (year % 100 != 0 or year % 400 = 0) then 366 else 365 end) as day_of_year_cos,
        sin(2 * pi() * week_of_year / 52) as week_of_year_sin,
        cos(2 * pi() * week_of_year / 52) as week_of_year_cos,
        case when date_part('month', sales_date) = 9 and day_of_month = 2 then 1 else 0 end as is_national_day,
        datediff('day', date '2019-01-01', sales_date) as days_since_2019
    from {{ ref('mart_forecast_daily_base') }}
),

ratios as (
    select
        *,
        cast(cogs as double) / nullif(revenue, 0) as cogs_ratio
    from base
),

calendar as (
    select
        b.*,
        t.tet_date,
        datediff('day', b.sales_date, t.tet_date) as days_to_tet
    from ratios as b
    left join {{ ref('tet_dates') }} as t
        on b.year = t.year
),

base_with_lags as (
    select
        sales_date,
        revenue,
        cogs,
        year,
        day_of_week,
        day_of_month,
        day_of_year,
        week_of_year,
        days_to_month_end,
        days_to_quarter_end,
        is_month_start,
        month_sin,
        month_cos,
        day_of_week_sin,
        day_of_week_cos,
        day_of_year_sin,
        day_of_year_cos,
        week_of_year_sin,
        week_of_year_cos,
        is_national_day,
        days_since_2019,
        cogs_ratio,
        tet_date,
        days_to_tet,

        lag(revenue, 1) over (order by sales_date) as lag_1d_revenue,
        lag(revenue, 2) over (order by sales_date) as lag_2d_revenue,
        lag(revenue, 3) over (order by sales_date) as lag_3d_revenue,
        lag(revenue, 7) over (order by sales_date) as lag_7d_revenue,
        lag(revenue, 8) over (order by sales_date) as lag_8d_revenue,
        lag(revenue, 29) over (order by sales_date) as lag_29d_revenue,
        lag(revenue, 14) over (order by sales_date) as lag_14d_revenue,
        lag(revenue, 28) over (order by sales_date) as lag_28d_revenue,
        lag(revenue, 365) over (order by sales_date) as lag_365d_revenue,

        lag(cogs, 1) over (order by sales_date) as lag_1d_cogs,
        lag(cogs, 7) over (order by sales_date) as lag_7d_cogs,
        lag(cogs, 28) over (order by sales_date) as lag_28d_cogs,
        lag(cogs, 365) over (order by sales_date) as lag_365d_cogs
    from calendar
),

lagged as (
    select
        sales_date,
        revenue,
        cogs,
        year,
        day_of_week,
        day_of_month,
        day_of_year,
        week_of_year,
        days_to_month_end,
        days_to_quarter_end,
        is_month_start,
        month_sin,
        month_cos,
        day_of_week_sin,
        day_of_week_cos,
        day_of_year_sin,
        day_of_year_cos,
        week_of_year_sin,
        week_of_year_cos,
        tet_date,
        days_to_tet,
        is_national_day,
        days_since_2019,
        cogs_ratio,

        lag_1d_revenue,
        lag_2d_revenue,
        lag_3d_revenue,
        lag_7d_revenue,
        lag_14d_revenue,
        lag_28d_revenue,
        lag_365d_revenue,
        lag_8d_revenue,
        lag_29d_revenue,

        cast(lag_1d_revenue as double) / nullif(lag_8d_revenue, 0) - 1
            as lag_1d_rev_wow_growth,
        cast(lag_1d_revenue as double) / nullif(lag_29d_revenue, 0) - 1
            as lag_1d_rev_mom_growth,
        cast(lag_1d_revenue as double) / nullif(lag_365d_revenue, 0) - 1
            as lag_1d_rev_yoy_growth,

        avg(lag_1d_revenue) over (
            order by sales_date rows between 6 preceding and current row
        ) as roll_mean_7d_revenue,
        avg(lag_1d_revenue) over (
            order by sales_date rows between 27 preceding and current row
        ) as roll_mean_28d_revenue,
        avg(lag_1d_revenue) over (
            order by sales_date rows between 364 preceding and current row
        ) as roll_mean_365d_revenue,

        median(lag_1d_revenue) over (
            order by sales_date rows between 6 preceding and current row
        ) as roll_median_7d_revenue,
        median(lag_1d_revenue) over (
            order by sales_date rows between 27 preceding and current row
        ) as roll_median_28d_revenue,

        stddev_samp(lag_1d_revenue) over (
            order by sales_date rows between 6 preceding and current row
        ) as roll_std_7d_revenue,
        stddev_samp(lag_1d_revenue) over (
            order by sales_date rows between 27 preceding and current row
        ) as roll_std_28d_revenue,
        stddev_samp(lag_1d_revenue) over (
            order by sales_date rows between 364 preceding and current row
        ) as roll_std_365d_revenue,

        avg(lag_1d_cogs) over (
            order by sales_date rows between 6 preceding and current row
        ) as roll_mean_7d_cogs,
        avg(lag_1d_cogs) over (
            order by sales_date rows between 27 preceding and current row
        ) as roll_mean_28d_cogs,
        stddev_samp(lag_1d_cogs) over (
            order by sales_date rows between 27 preceding and current row
        ) as roll_std_28d_cogs,

        lag_1d_cogs,
        lag_7d_cogs,
        lag_28d_cogs,
        lag_365d_cogs,

        lag_365d_revenue as revenue_baseline,
        lag_365d_cogs as cogs_baseline,
        case when lag_365d_revenue is null then null
             else revenue - lag_365d_revenue
        end as revenue_residual,
        case when lag_365d_cogs is null then null
             else cogs - lag_365d_cogs
        end as cogs_residual
    from base_with_lags
),

with_residual_lags as (
    select
        *,
        lag(revenue_residual, 1) over (order by sales_date) as lag_1d_rev_residual,
        lag(revenue_residual, 2) over (order by sales_date) as lag_2d_rev_residual,
        lag(revenue_residual, 3) over (order by sales_date) as lag_3d_rev_residual,
        lag(revenue_residual, 7) over (order by sales_date) as lag_7d_rev_residual,
        lag(cogs_residual, 1) over (order by sales_date) as lag_1d_cogs_residual,
        lag(cogs_residual, 2) over (order by sales_date) as lag_2d_cogs_residual,
        lag(cogs_residual, 3) over (order by sales_date) as lag_3d_cogs_residual,
        lag(cogs_residual, 7) over (order by sales_date) as lag_7d_cogs_residual
    from lagged
),

enriched as (
    select
        *,
        lag_1d_rev_wow_growth - lag(lag_1d_rev_wow_growth, 1) over (order by sales_date)
            as rev_wow_acceleration,
        lag_1d_rev_mom_growth - lag(lag_1d_rev_mom_growth, 1) over (order by sales_date)
            as rev_mom_acceleration,
        lag_1d_rev_yoy_growth - lag(lag_1d_rev_yoy_growth, 1) over (order by sales_date)
            as rev_yoy_acceleration
    from with_residual_lags
)

select *
from enriched