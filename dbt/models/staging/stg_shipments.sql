select
    cast(order_id as bigint) as order_id,
    try_cast(ship_date as date) as ship_date,
    try_cast(delivery_date as date) as delivery_date,
    cast(shipping_fee as double) as shipping_fee
from {{ source('raw', 'shipments') }}
