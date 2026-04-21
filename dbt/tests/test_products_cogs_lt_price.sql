select
    product_id,
    price,
    cogs
from {{ ref('stg_products') }}
where cogs >= price
