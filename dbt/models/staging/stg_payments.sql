select
    cast(order_id as bigint) as order_id,
    lower(trim(payment_method)) as payment_method,
    cast(payment_value as double) as payment_value,
    cast(installments as integer) as installments
from {{ source('raw', 'payments') }}
