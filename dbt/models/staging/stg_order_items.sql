select
    cast(order_id as bigint) as order_id,
    cast(product_id as bigint) as product_id,
    cast(quantity as bigint) as quantity,
    cast(unit_price as double) as unit_price,
    cast(discount_amount as double) as discount_amount,
    nullif(trim(promo_id), '') as promo_id,
    nullif(trim(promo_id_2), '') as promo_id_2
from {{ source('raw', 'order_items') }}
