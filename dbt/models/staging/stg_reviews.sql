select
    trim(review_id) as review_id,
    cast(order_id as bigint) as order_id,
    cast(product_id as bigint) as product_id,
    cast(customer_id as bigint) as customer_id,
    try_cast(review_date as date) as review_date,
    cast(rating as integer) as rating,
    trim(review_title) as review_title
from {{ source('raw', 'reviews') }}
