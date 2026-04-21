select
    trim(return_id) as return_id,
    cast(order_id as bigint) as order_id,
    cast(product_id as bigint) as product_id,
    try_cast(return_date as date) as return_date,
    lower(trim(return_reason)) as return_reason,
    cast(return_quantity as bigint) as return_quantity,
    cast(refund_amount as double) as refund_amount
from {{ source('raw', 'returns') }}
