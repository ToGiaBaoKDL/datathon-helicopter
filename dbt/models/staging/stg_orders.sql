select
    cast(order_id as bigint) as order_id,
    try_cast(order_date as date) as order_date,
    cast(customer_id as bigint) as customer_id,
    cast(zip as bigint) as zip,
    lower(trim(order_status)) as order_status,
    lower(trim(payment_method)) as payment_method,
    lower(trim(cast(device_type as varchar))) as device_type,
    lower(trim(cast(order_source as varchar))) as order_source
from {{ source('raw', 'orders') }}
