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
    coalesce(order_count, 0) as order_count,
    coalesce(order_line_count, 0) as order_line_count,
    coalesce(units_sold, 0) as units_sold,
    coalesce(line_revenue, 0) as line_revenue,
    coalesce(line_cogs, 0) as line_cogs,
    coalesce(total_discount_amount, 0) as total_discount_amount,
    avg_line_revenue,
    coalesce(promo_line_count, 0) as promo_line_count,
    coalesce(cancelled_line_count, 0) as cancelled_line_count,
    coalesce(return_record_count, 0) as return_record_count,
    coalesce(return_units, 0) as return_units,
    coalesce(refund_amount_total, 0) as refund_amount_total,
    coalesce(review_count, 0) as review_count,
    avg_rating,
    coalesce(sessions, 0) as sessions,
    coalesce(unique_visitors, 0) as unique_visitors,
    coalesce(page_views, 0) as page_views,
    coalesce(avg_bounce_rate, 0) as avg_bounce_rate,
    coalesce(avg_session_duration_sec, 0) as avg_session_duration_sec,
    coalesce(lag_1m_stock_on_hand_total, 0) as lag_1m_stock_on_hand_total,
    coalesce(lag_1m_units_received_total, 0) as lag_1m_units_received_total,
    coalesce(lag_1m_units_sold_total, 0) as lag_1m_units_sold_total,
    coalesce(lag_1m_avg_stockout_days, 0) as lag_1m_avg_stockout_days,
    coalesce(lag_1m_avg_days_of_supply, 0) as lag_1m_avg_days_of_supply,
    coalesce(lag_1m_avg_fill_rate, 0) as lag_1m_avg_fill_rate,
    coalesce(lag_1m_avg_sell_through_rate, 0) as lag_1m_avg_sell_through_rate,
    coalesce(lag_1m_stockout_flag_count, 0) as lag_1m_stockout_flag_count,
    coalesce(lag_1m_overstock_flag_count, 0) as lag_1m_overstock_flag_count,
    coalesce(lag_1m_reorder_flag_count, 0) as lag_1m_reorder_flag_count
from joined
