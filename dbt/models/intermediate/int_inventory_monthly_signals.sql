with monthly_inventory as (
    select
        date_trunc('month', snapshot_date) as month_start_date,
        sum(stock_on_hand) as stock_on_hand_total,
        sum(units_received) as units_received_total,
        sum(units_sold) as units_sold_total,
        avg(stockout_days) as avg_stockout_days,
        avg(days_of_supply) as avg_days_of_supply,
        avg(fill_rate) as avg_fill_rate,
        avg(sell_through_rate) as avg_sell_through_rate,
        sum(stockout_flag) as stockout_flag_count,
        sum(overstock_flag) as overstock_flag_count,
        sum(reorder_flag) as reorder_flag_count
    from {{ ref('stg_inventory') }}
    group by 1
)

select
    month_start_date,
    lag(stock_on_hand_total, 1) over (order by month_start_date) as lag_1m_stock_on_hand_total,
    lag(units_received_total, 1) over (order by month_start_date) as lag_1m_units_received_total,
    lag(units_sold_total, 1) over (order by month_start_date) as lag_1m_units_sold_total,
    lag(avg_stockout_days, 1) over (order by month_start_date) as lag_1m_avg_stockout_days,
    lag(avg_days_of_supply, 1) over (order by month_start_date) as lag_1m_avg_days_of_supply,
    lag(avg_fill_rate, 1) over (order by month_start_date) as lag_1m_avg_fill_rate,
    lag(avg_sell_through_rate, 1) over (order by month_start_date) as lag_1m_avg_sell_through_rate,
    lag(stockout_flag_count, 1) over (order by month_start_date) as lag_1m_stockout_flag_count,
    lag(overstock_flag_count, 1) over (order by month_start_date) as lag_1m_overstock_flag_count,
    lag(reorder_flag_count, 1) over (order by month_start_date) as lag_1m_reorder_flag_count
from monthly_inventory
