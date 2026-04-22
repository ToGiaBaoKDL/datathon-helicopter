with base as (
    select
        sales_date,
        revenue,
        cogs,
        year,
        month,
        day_of_week,
        is_weekend,
        date_part('quarter', sales_date) as quarter,
        date_part('day', sales_date) as day_of_month,
        datediff('day', sales_date, date_trunc('month', sales_date) + interval '1 month')
            as days_to_month_end,
        case when date_part('day', sales_date) <= 3 then 1 else 0 end as is_month_start,
        case when date_part('day', sales_date) > 28 then 1 else 0 end as is_month_end,
        sin(2 * pi() * month / 12) as month_sin,
        cos(2 * pi() * month / 12) as month_cos,
        sin(2 * pi() * day_of_week / 7) as day_of_week_sin,
        cos(2 * pi() * day_of_week / 7) as day_of_week_cos,
        order_count,
        units_sold,
        total_discount_amount,
        promo_line_count,
        cancelled_line_count,
        return_record_count,
        return_units,
        sessions,
        unique_visitors,
        page_views,
        avg_bounce_rate,
        avg_session_duration_sec,
        lag_1m_stock_on_hand_total,
        lag_1m_units_received_total,
        lag_1m_units_sold_total,
        lag_1m_avg_stockout_days,
        lag_1m_avg_days_of_supply,
        lag_1m_avg_fill_rate,
        lag_1m_avg_sell_through_rate,
        lag_1m_stockout_flag_count,
        lag_1m_overstock_flag_count,
        lag_1m_reorder_flag_count
    from {{ ref('mart_forecast_daily_base') }}
),

calendar as (
    select
        b.*,
        t.tet_date,
        datediff('day', b.sales_date, t.tet_date) as days_to_tet,
        case when datediff('day', b.sales_date, t.tet_date) between 1 and 21 then 1 else 0 end as is_pre_tet_rush,
        case when datediff('day', b.sales_date, t.tet_date) between 0 and 6  then 1 else 0 end as is_tet_holiday,
        case when datediff('day', b.sales_date, t.tet_date) between -14 and -7 then 1 else 0 end as is_post_tet
    from base as b
    left join {{ ref('tet_dates') }} as t
        on b.year = t.year
),

base_with_lags as (
    select
        sales_date,
        revenue,
        cogs,
        year,
        month,
        day_of_week,
        is_weekend,
        quarter,
        day_of_month,
        days_to_month_end,
        is_month_start,
        is_month_end,
        month_sin,
        month_cos,
        day_of_week_sin,
        day_of_week_cos,
        tet_date,
        days_to_tet,
        is_pre_tet_rush,
        is_tet_holiday,
        is_post_tet,

        lag(revenue, 1) over (order by sales_date) as lag_1d_revenue,
        lag(revenue, 7) over (order by sales_date) as lag_7d_revenue,
        lag(revenue, 14) over (order by sales_date) as lag_14d_revenue,
        lag(revenue, 28) over (order by sales_date) as lag_28d_revenue,

        lag(cogs, 1) over (order by sales_date) as lag_1d_cogs,
        lag(order_count, 1) over (order by sales_date) as lag_1d_order_count,
        lag(order_count, 7) over (order by sales_date) as lag_7d_order_count,
        lag(units_sold, 1) over (order by sales_date) as lag_1d_units_sold,
        lag(units_sold, 7) over (order by sales_date) as lag_7d_units_sold,
        lag(total_discount_amount, 1) over (order by sales_date) as lag_1d_total_discount_amount,
        lag(promo_line_count, 1) over (order by sales_date) as lag_1d_promo_line_count,
        lag(cancelled_line_count, 1) over (order by sales_date) as lag_1d_cancelled_line_count,
        lag(return_record_count, 1) over (order by sales_date) as lag_1d_return_record_count,
        lag(return_units, 1) over (order by sales_date) as lag_1d_return_units,
        lag(sessions, 1) over (order by sales_date) as lag_1d_sessions,
        lag(sessions, 7) over (order by sales_date) as lag_7d_sessions,
        lag(unique_visitors, 1) over (order by sales_date) as lag_1d_unique_visitors,
        lag(page_views, 1) over (order by sales_date) as lag_1d_page_views,
        lag(avg_bounce_rate, 1) over (order by sales_date) as lag_1d_avg_bounce_rate,
        lag(avg_session_duration_sec, 1) over (order by sales_date) as lag_1d_avg_session_duration_sec,

        lag_1m_stock_on_hand_total,
        lag_1m_units_received_total,
        lag_1m_units_sold_total,
        lag_1m_avg_stockout_days,
        lag_1m_avg_days_of_supply,
        lag_1m_avg_fill_rate,
        lag_1m_avg_sell_through_rate,
        lag_1m_stockout_flag_count,
        lag_1m_overstock_flag_count,
        lag_1m_reorder_flag_count
    from calendar
),

lagged as (
    select
        sales_date,
        revenue,
        cogs,
        year,
        month,
        quarter,
        day_of_week,
        is_weekend,
        day_of_month,
        days_to_month_end,
        is_month_start,
        is_month_end,
        month_sin,
        month_cos,
        day_of_week_sin,
        day_of_week_cos,
        tet_date,
        days_to_tet,
        is_pre_tet_rush,
        is_tet_holiday,
        is_post_tet,

        lag_1d_revenue,
        lag_7d_revenue,
        lag_14d_revenue,
        lag_28d_revenue,

        avg(lag_1d_revenue) over (
            order by sales_date rows between 6 preceding and current row
        ) as roll_mean_7d_revenue,
        avg(lag_1d_revenue) over (
            order by sales_date rows between 27 preceding and current row
        ) as roll_mean_28d_revenue,

        stddev_samp(lag_1d_revenue) over (
            order by sales_date rows between 6 preceding and current row
        ) as roll_std_7d_revenue,
        stddev_samp(lag_1d_revenue) over (
            order by sales_date rows between 27 preceding and current row
        ) as roll_std_28d_revenue,

        lag_1d_cogs,
        lag_1d_order_count,
        lag_7d_order_count,
        lag_1d_units_sold,
        lag_7d_units_sold,
        lag_1d_total_discount_amount,
        lag_1d_promo_line_count,
        lag_1d_cancelled_line_count,
        lag_1d_return_record_count,
        lag_1d_return_units,
        lag_1d_sessions,
        lag_7d_sessions,
        lag_1d_unique_visitors,
        lag_1d_page_views,
        lag_1d_avg_bounce_rate,
        lag_1d_avg_session_duration_sec,

        avg(lag_1d_sessions) over (
            order by sales_date rows between 6 preceding and current row
        ) as roll_mean_7d_sessions,
        avg(lag_1d_order_count) over (
            order by sales_date rows between 6 preceding and current row
        ) as roll_mean_7d_order_count,
        avg(lag_1d_units_sold) over (
            order by sales_date rows between 6 preceding and current row
        ) as roll_mean_7d_units_sold,

        lag_1m_stock_on_hand_total,
        lag_1m_units_received_total,
        lag_1m_units_sold_total,
        lag_1m_avg_stockout_days,
        lag_1m_avg_days_of_supply,
        lag_1m_avg_fill_rate,
        lag_1m_avg_sell_through_rate,
        lag_1m_stockout_flag_count,
        lag_1m_overstock_flag_count,
        lag_1m_reorder_flag_count
    from base_with_lags
)

select *
from lagged
