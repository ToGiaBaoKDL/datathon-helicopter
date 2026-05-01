with base as (
    select
        sales_date,
        revenue,
        cogs,
        order_count,
        units_sold,
        sessions,
        year,
        day_of_week,
        date_part('dayofyear', sales_date) as day_of_year,
        date_part('day', sales_date) as day_of_month,
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
        sin(2 * pi() * month / 12) as month_sin,
        cos(2 * pi() * month / 12) as month_cos,
        datediff('day', date '2019-01-01', sales_date) as days_since_2019,
        case when day_of_month <= 3 then 1 else 0 end as is_month_start_window,
        case when days_to_month_end <= 4 then 1 else 0 end as is_month_end_window
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

-- Day-of-month seasonal profiles (known-in-advance, captures salary cycle)
day_of_month_profiles as (
    select
        date_part('day', sales_date) as day_of_month,
        avg(revenue) as hist_avg_revenue_dom,
        avg(cogs) as hist_avg_cogs_dom
    from ratios
    group by date_part('day', sales_date)
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

-- Sale season hardcoded windows (domain knowledge from top notebook)
sale_season_windows as (
    select * from (values
        (1, 30, 30, 1),
        (3, 18, 30, 2),
        (6, 23, 29, 3),
        (7, 30, 34, 5),
        (8, 30, 32, 4),
        (11, 18, 45, 6)
    ) as t(month, start_day, duration, profit_rank)
),

years as (
    select generate_series as yr from generate_series(2012, 2024)
),

sale_season_dates as (
    select
        unnest(generate_series(
            make_date(y.yr, w.month, w.start_day),
            make_date(y.yr, w.month, w.start_day) + interval '1 day' * (w.duration - 1),
            interval '1 day'
        ))::date as sale_date,
        w.profit_rank as sale_rank
    from sale_season_windows w
    cross join years y
),

sale_flags as (
    select
        b.sales_date,
        max(case when s.sale_date is not null then 1 else 0 end) as is_sale_season,
        max(coalesce(s.sale_rank, 0)) as sale_rank
    from base b
    left join sale_season_dates s on b.sales_date = s.sale_date
    group by b.sales_date
),

sale_next as (
    select
        b.sales_date,
        coalesce(min(datediff('day', b.sales_date, s.sale_date)), 999) as days_to_next_sale
    from base b
    left join sale_season_dates s on s.sale_date >= b.sales_date
    group by b.sales_date
),

sale_prev as (
    select
        b.sales_date,
        coalesce(min(datediff('day', s.sale_date, b.sales_date)), 999) as days_since_last_sale
    from base b
    left join sale_season_dates s on s.sale_date <= b.sales_date
    group by b.sales_date
),

peak_dates as (
    select make_date(y, m, 1)::date as peak_date
    from generate_series(2012, 2024) as y(y)
    cross join (values (4), (5), (11)) as t(m)
),

peak_next as (
    select
        b.sales_date,
        coalesce(min(datediff('day', b.sales_date, p.peak_date)), 999) as days_to_next_peak
    from base b
    left join peak_dates p on p.peak_date >= b.sales_date
    group by b.sales_date
),

peak_prev as (
    select
        b.sales_date,
        coalesce(min(datediff('day', p.peak_date, b.sales_date)), 999) as days_since_last_peak
    from base b
    left join peak_dates p on p.peak_date <= b.sales_date
    group by b.sales_date
),

peak_features as (
    select
        b.sales_date,
        case when b.month in (4, 5, 11) then 1 else 0 end as is_peak_season,
        1.0 / (1.0 + least(
            coalesce(pn.days_to_next_peak, 999),
            coalesce(pp.days_since_last_peak, 999)
        )) as peak_proximity
    from base b
    left join peak_next pn on b.sales_date = pn.sales_date
    left join peak_prev pp on b.sales_date = pp.sales_date
),

calendar as (
    select
        b.*,
        dp.hist_avg_revenue_dow,
        dp.hist_avg_cogs_dow,
        mp.hist_avg_revenue_month,
        mp.hist_avg_cogs_month,
        domp.hist_avg_revenue_dom,
        domp.hist_avg_cogs_dom,
        gs.overall_avg_revenue,
        gs.overall_avg_cogs,
        coalesce(pp.promo_month_day_count, 0) as promo_month_day_count,
        coalesce(pp.promo_month_prob, 0) as promo_month_prob,
        coalesce(pp.promo_month_avg_discount, 0) as promo_month_avg_discount,
        coalesce(sf.is_sale_season, 0) as is_sale_season,
        coalesce(sf.sale_rank, 0) as sale_rank,
        coalesce(sn.days_to_next_sale, 999) as days_to_next_sale,
        coalesce(sp.days_since_last_sale, 999) as days_since_last_sale,
        coalesce(pf.is_peak_season, 0) as is_peak_season,
        coalesce(pf.peak_proximity, 0.0) as peak_proximity
    from ratios as b
    cross join global_stats as gs
    left join dow_profiles as dp on b.day_of_week = dp.day_of_week
    left join month_profiles as mp on b.month = mp.month
    left join day_of_month_profiles as domp on b.day_of_month = domp.day_of_month
    left join promo_profiles as pp on b.month = pp.month
    left join sale_flags sf on b.sales_date = sf.sales_date
    left join sale_next sn on b.sales_date = sn.sales_date
    left join sale_prev sp on b.sales_date = sp.sales_date
    left join peak_features pf on b.sales_date = pf.sales_date
),

base_with_lags as (
    select
        sales_date,
        revenue,
        cogs,
        order_count,
        units_sold,
        sessions,
        year,
        day_of_week,
        day_of_year,
        day_of_month,
        month,
        days_to_month_end,
        days_to_quarter_end,
        day_of_week_sin,
        day_of_week_cos,
        day_of_year_sin,
        day_of_year_cos,
        month_sin,
        month_cos,
        days_since_2019,
        is_month_start_window,
        is_month_end_window,
        cogs_ratio,
        hist_avg_revenue_dow,
        hist_avg_cogs_dow,
        hist_avg_revenue_month,
        hist_avg_cogs_month,
        hist_avg_revenue_dom,
        hist_avg_cogs_dom,
        overall_avg_revenue,
        overall_avg_cogs,
        promo_month_day_count,
        promo_month_prob,
        promo_month_avg_discount,
        is_sale_season,
        sale_rank,
        days_to_next_sale,
        days_since_last_sale,
        is_peak_season,
        peak_proximity,

        lag(revenue, 1) over (order by sales_date) as lag_1d_revenue,
        lag(revenue, 2) over (order by sales_date) as lag_2d_revenue,
        lag(revenue, 3) over (order by sales_date) as lag_3d_revenue,
        lag(revenue, 7) over (order by sales_date) as lag_7d_revenue,
        lag(revenue, 8) over (order by sales_date) as lag_8d_revenue,
        lag(revenue, 29) over (order by sales_date) as lag_29d_revenue,
        lag(revenue, 14) over (order by sales_date) as lag_14d_revenue,
        lag(revenue, 28) over (order by sales_date) as lag_28d_revenue,
        lag(revenue, 90) over (order by sales_date) as lag_90d_revenue,
        lag(revenue, 180) over (order by sales_date) as lag_180d_revenue,
        lag(revenue, 364) over (order by sales_date) as lag_364d_revenue,
        lag(revenue, 365) over (order by sales_date) as lag_365d_revenue,
        lag(revenue, 366) over (order by sales_date) as lag_366d_revenue,
        lag(revenue, 730) over (order by sales_date) as lag_730d_revenue,

        lag(cogs, 1) over (order by sales_date) as lag_1d_cogs,
        lag(cogs, 7) over (order by sales_date) as lag_7d_cogs,
        lag(cogs, 28) over (order by sales_date) as lag_28d_cogs,
        lag(cogs, 365) over (order by sales_date) as lag_365d_cogs,
        lag(cogs, 730) over (order by sales_date) as lag_730d_cogs,

        lag(cogs_ratio, 1) over (order by sales_date) as lag_1d_cogs_ratio,

        -- Exogenous lags (730d = fully safe for 548-day horizon)
        lag(order_count, 730) over (order by sales_date) as lag_730d_order_count,
        lag(units_sold, 730) over (order by sales_date) as lag_730d_units_sold,
        lag(sessions, 730) over (order by sales_date) as lag_730d_sessions
    from calendar
),

lagged as (
    select
        sales_date,
        revenue,
        cogs,
        order_count,
        units_sold,
        sessions,
        year,
        day_of_week,
        day_of_year,
        day_of_month,
        month,
        days_to_month_end,
        days_to_quarter_end,
        day_of_week_sin,
        day_of_week_cos,
        day_of_year_sin,
        day_of_year_cos,
        month_sin,
        month_cos,
        days_since_2019,
        is_month_start_window,
        is_month_end_window,
        cogs_ratio,
        hist_avg_revenue_dow,
        hist_avg_cogs_dow,
        hist_avg_revenue_month,
        hist_avg_cogs_month,
        hist_avg_revenue_dom,
        hist_avg_cogs_dom,
        overall_avg_revenue,
        overall_avg_cogs,
        promo_month_day_count,
        promo_month_prob,
        promo_month_avg_discount,
        is_sale_season,
        sale_rank,
        days_to_next_sale,
        days_since_last_sale,
        is_peak_season,
        peak_proximity,

        lag_1d_revenue,
        lag_2d_revenue,
        lag_3d_revenue,
        lag_7d_revenue,
        lag_8d_revenue,
        lag_14d_revenue,
        lag_28d_revenue,
        lag_29d_revenue,
        lag_90d_revenue,
        lag_180d_revenue,
        lag_364d_revenue,
        lag_365d_revenue,
        lag_366d_revenue,
        lag_730d_revenue,

        lag_1d_cogs,
        lag_7d_cogs,
        lag_28d_cogs,
        lag_365d_cogs,
        lag_730d_cogs,

        -- Exogenous lags (730d safe for 548-day horizon)
        lag_730d_order_count,
        lag_730d_units_sold,
        lag_730d_sessions,

        -- Day-of-month ratio (how much above/below typical for this day-of-month)
        case when hist_avg_revenue_dom is null or hist_avg_revenue_dom = 0 then null
             else revenue / hist_avg_revenue_dom
        end as day_of_month_ratio,

        -- Revenue rolling windows
        avg(lag_1d_revenue) over (
            order by sales_date rows between 29 preceding and current row
        ) as roll_mean_30d_revenue,
        stddev_samp(lag_1d_revenue) over (
            order by sales_date rows between 29 preceding and current row
        ) as roll_std_30d_revenue,

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

        -- Growth ratios
        case when lag_8d_revenue is null or lag_8d_revenue = 0 then null
             else lag_1d_revenue / lag_8d_revenue - 1
        end as lag_1d_rev_wow_growth,
        case when lag_29d_revenue is null or lag_29d_revenue = 0 then null
             else lag_1d_revenue / lag_29d_revenue - 1
        end as lag_1d_rev_mom_growth,
        case when lag_365d_revenue is null or lag_365d_revenue = 0 then null
             else lag_1d_revenue / lag_365d_revenue - 1
        end as lag_1d_rev_yoy_growth,

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
        end as naive_cogs_residual,

        -- YoY delta and rolling
        lag_1d_revenue - lag_365d_revenue as rev_yoy_delta,
        case when lag_730d_revenue is null or lag_730d_revenue = 0 then null
             else lag_365d_revenue / lag_730d_revenue - 1
        end as rev_2yr_ratio
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
