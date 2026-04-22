with target as (
    select
        sales_date,
        revenue,
        cogs
    from {{ ref('stg_sales') }}
),

commercial as (
    select *
    from {{ ref('int_daily_commercial_signals') }}
),

inventory_monthly as (
    select *
    from {{ ref('int_inventory_monthly_signals') }}
),

joined as (
    select
        t.sales_date,
        t.revenue,
        t.cogs,
        c.order_count,
        c.order_line_count,
        c.units_sold,
        c.line_revenue,
        c.line_cogs,
        c.total_discount_amount,
        c.avg_line_revenue,
        c.promo_line_count,
        c.cancelled_line_count,
        c.return_record_count,
        c.return_units,
        c.refund_amount_total,
        c.review_count,
        c.avg_rating,
        c.sessions,
        c.unique_visitors,
        c.page_views,
        c.avg_bounce_rate,
        c.avg_session_duration_sec,
        i.lag_1m_stock_on_hand_total,
        i.lag_1m_units_received_total,
        i.lag_1m_units_sold_total,
        i.lag_1m_avg_stockout_days,
        i.lag_1m_avg_days_of_supply,
        i.lag_1m_avg_fill_rate,
        i.lag_1m_avg_sell_through_rate,
        i.lag_1m_stockout_flag_count,
        i.lag_1m_overstock_flag_count,
        i.lag_1m_reorder_flag_count
    from target as t
    left join commercial as c
        on t.sales_date = c.sales_date
    left join inventory_monthly as i
        on date_trunc('month', t.sales_date) = i.month_start_date
)

select
    sales_date,
    revenue,
    cogs,
    date_part('year', sales_date) as year,
    date_part('month', sales_date) as month,
    date_part('dayofweek', sales_date) as day_of_week,
    case when date_part('dayofweek', sales_date) in (0, 6) then 1 else 0 end as is_weekend,
    order_count,
    order_line_count,
    units_sold,
    line_revenue,
    line_cogs,
    total_discount_amount,
    avg_line_revenue,
    promo_line_count,
    cancelled_line_count,
    return_record_count,
    return_units,
    refund_amount_total,
    review_count,
    avg_rating,
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
from joined
