select
    trim(promo_id) as promo_id,
    trim(promo_name) as promo_name,
    lower(trim(promo_type)) as promo_type,
    cast(discount_value as double) as discount_value,
    try_cast(start_date as date) as start_date,
    try_cast(end_date as date) as end_date,
    nullif(trim(applicable_category), '') as applicable_category,
    nullif(lower(trim(promo_channel)), '') as promo_channel,
    cast(stackable_flag as integer) as stackable_flag,
    cast(min_order_value as double) as min_order_value
from {{ source('raw', 'promotions') }}
