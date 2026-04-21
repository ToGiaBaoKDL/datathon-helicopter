select
    snapshot_date as sales_date,
    sum(stock_on_hand) as stock_on_hand_total,
    sum(units_received) as units_received_total,
    sum(units_sold) as units_sold_total,
    avg(stockout_days) as avg_stockout_days,
    avg(days_of_supply) as avg_days_of_supply,
    avg(fill_rate) as avg_fill_rate,
    avg(sell_through_rate) as avg_sell_through_rate,
    sum(stockout_flag) as stockout_product_count,
    sum(overstock_flag) as overstock_product_count,
    sum(reorder_flag) as reorder_product_count
from {{ ref('stg_inventory') }}
group by 1
