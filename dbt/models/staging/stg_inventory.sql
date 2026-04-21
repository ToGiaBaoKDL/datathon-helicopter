select
    try_cast(snapshot_date as date) as snapshot_date,
    cast(product_id as bigint) as product_id,
    cast(stock_on_hand as double) as stock_on_hand,
    cast(units_received as double) as units_received,
    cast(units_sold as double) as units_sold,
    cast(stockout_days as double) as stockout_days,
    cast(days_of_supply as double) as days_of_supply,
    cast(fill_rate as double) as fill_rate,
    cast(stockout_flag as integer) as stockout_flag,
    cast(overstock_flag as integer) as overstock_flag,
    cast(reorder_flag as integer) as reorder_flag,
    cast(sell_through_rate as double) as sell_through_rate,
    trim(cast(product_name as varchar)) as product_name,
    trim(category) as category,
    trim(segment) as segment,
    cast(year as integer) as year,
    cast(month as integer) as month
from {{ source('raw', 'inventory') }}
