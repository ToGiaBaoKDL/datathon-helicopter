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
        date_part('month', sales_date) as month,
        datediff('day', sales_date, date_trunc('month', sales_date) + interval '1 month')
            as days_to_month_end,
        datediff(
            'day',
            sales_date,
            date_trunc('quarter', sales_date) + interval '3 months' - interval '1 day'
        ) as days_to_quarter_end,
        sin(2 * pi() * day_of_week / 7) as day_of_week_sin,
        cos(2 * pi() * day_of_week / 7) as day_of_week_cos,
        sin(2 * pi() * day_of_year / case when year % 4 = 0 and (year % 100 != 0 or year % 400 = 0) then 366 else 365 end) as day_of_year_sin,
        cos(2 * pi() * day_of_year / case when year % 4 = 0 and (year % 100 != 0 or year % 400 = 0) then 366 else 365 end) as day_of_year_cos,
        sin(2 * pi() * week_of_year / 52) as week_of_year_sin,
        cos(2 * pi() * week_of_year / 52) as week_of_year_cos,
        datediff('day', date '2019-01-01', sales_date) as days_since_2019
    from {{ ref('mart_forecast_daily_base') }}
),

ratios as (
    select
        *,
        cast(cogs as double) / nullif(revenue, 0) as cogs_ratio
    from base
),

-- Global averages for seasonal decomposition
global_stats as (
    select
        avg(revenue) as overall_avg_revenue,
        avg(cogs) as overall_avg_cogs
    from ratios
),

-- Day-of-week seasonal profiles (known-in-advance)
dow_profiles as (
    select
        day_of_week,
        avg(revenue) as hist_avg_revenue_dow,
        avg(cogs) as hist_avg_cogs_dow
    from ratios
    group by day_of_week
),

-- Month-of-year seasonal profiles (known-in-advance)
month_profiles as (
    select
        month,
        avg(revenue) as hist_avg_revenue_month,
        avg(cogs) as hist_avg_cogs_month
    from ratios
    group by month
),

-- Promo calendar profiles (known-in-advance seasonal pattern)
promo_profiles_raw as (
    select
        date_part('month', dt) as month,
        count(distinct dt) as promo_month_day_count,
        count(distinct date_part('year', dt)) as years_with_promo,
        avg(discount_value) as promo_month_avg_discount
    from (
        select
            unnest(generate_series(start_date, end_date, interval '1 day'))::date as dt,
            discount_value
        from {{ ref('stg_promotions') }}
    )
    group by date_part('month', dt)
),

promo_profiles as (
    select
        month,
        promo_month_day_count,
        promo_month_day_count::float
            / nullif(years_with_promo, 0)
            / case
                  when month in (1, 3, 5, 7, 8, 10, 12) then 31
                  when month = 2 then 28.25
                  else 30
              end as promo_month_prob,
        promo_month_avg_discount
    from promo_profiles_raw
),

calendar as (
    select
        b.*,
        dp.hist_avg_revenue_dow,
        dp.hist_avg_cogs_dow,
        mp.hist_avg_revenue_month,
        mp.hist_avg_cogs_month,
        gs.overall_avg_revenue,
        gs.overall_avg_cogs,
        coalesce(pp.promo_month_day_count, 0) as promo_month_day_count,
        coalesce(pp.promo_month_prob, 0) as promo_month_prob,
        coalesce(pp.promo_month_avg_discount, 0) as promo_month_avg_discount
    from ratios as b
    cross join global_stats as gs
    left join dow_profiles as dp on b.day_of_week = dp.day_of_week
    left join month_profiles as mp on b.month = mp.month
    left join promo_profiles as pp on b.month = pp.month
),

base_with_lags as (
    select
        sales_date,
        revenue,
        cogs,
        year,
        day_of_week,
        day_of_year,
        week_of_year,
        month,
        days_to_month_end,
        days_to_quarter_end,
        day_of_week_sin,
        day_of_week_cos,
        day_of_year_sin,
        day_of_year_cos,
        days_since_2019,
        cogs_ratio,
        hist_avg_revenue_dow,
        hist_avg_cogs_dow,
        hist_avg_revenue_month,
        hist_avg_cogs_month,
        overall_avg_revenue,
        overall_avg_cogs,
        promo_month_day_count,
        promo_month_prob,
        promo_month_avg_discount,

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
        lag(cogs, 365) over (order by sales_date) as lag_365d_cogs,

        lag(cogs_ratio, 1) over (order by sales_date) as lag_1d_cogs_ratio
    from calendar
),

lagged as (
    select
        sales_date,
        revenue,
        cogs,
        year,
        day_of_week,
        day_of_year,
        week_of_year,
        month,
        days_to_month_end,
        days_to_quarter_end,
        day_of_week_sin,
        day_of_week_cos,
        day_of_year_sin,
        day_of_year_cos,
        days_since_2019,
        cogs_ratio,
        hist_avg_revenue_dow,
        hist_avg_cogs_dow,
        hist_avg_revenue_month,
        hist_avg_cogs_month,
        overall_avg_revenue,
        overall_avg_cogs,
        promo_month_day_count,
        promo_month_prob,
        promo_month_avg_discount,

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

        -- COGS ratio rolling
        avg(lag_1d_cogs_ratio) over (
            order by sales_date rows between 6 preceding and current row
        ) as roll_mean_7d_cogs_ratio,
        avg(lag_1d_cogs_ratio) over (
            order by sales_date rows between 27 preceding and current row
        ) as roll_mean_28d_cogs_ratio,
        stddev_samp(lag_1d_cogs_ratio) over (
            order by sales_date rows between 27 preceding and current row
        ) as roll_std_28d_cogs_ratio,

        lag_1d_cogs_ratio,

        -- First-difference momentum (1d vs 7d)
        lag_1d_revenue - lag_7d_revenue as revenue_diff_7d,
        lag_1d_cogs - lag_7d_cogs as cogs_diff_7d,

        -- Seasonal baseline (primary: additive decomposition dow + month - overall)
        hist_avg_revenue_dow + hist_avg_revenue_month - overall_avg_revenue
            as revenue_baseline,
        hist_avg_cogs_dow + hist_avg_cogs_month - overall_avg_cogs
            as cogs_baseline,

        -- Residuals against seasonal baseline (primary for modeling)
        revenue - (hist_avg_revenue_dow + hist_avg_revenue_month - overall_avg_revenue)
            as revenue_residual,
        cogs - (hist_avg_cogs_dow + hist_avg_cogs_month - overall_avg_cogs)
            as cogs_residual,

        -- Naive YoY residual (kept as reference feature)
        case when lag_365d_revenue is null then null
             else revenue - lag_365d_revenue
        end as naive_revenue_residual,
        case when lag_365d_cogs is null then null
             else cogs - lag_365d_cogs
        end as naive_cogs_residual
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

select * from enriched
