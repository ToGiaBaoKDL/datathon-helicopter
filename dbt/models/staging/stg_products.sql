select
    cast(product_id as bigint) as product_id,
    trim(cast(product_name as varchar)) as product_name,
    trim(category) as category,
    trim(segment) as segment,
    trim(size) as size,
    trim(color) as color,
    cast(price as double) as price,
    cast(cogs as double) as cogs,
    (cast(price as double) - cast(cogs as double)) / nullif(cast(price as double), 0) as gross_margin_rate
from {{ source('raw', 'products') }}
