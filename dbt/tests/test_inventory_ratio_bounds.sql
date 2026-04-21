select
    snapshot_date,
    product_id,
    fill_rate,
    sell_through_rate
from {{ ref('stg_inventory') }}
where fill_rate < 0
   or fill_rate > 1
   or sell_through_rate < 0
   or sell_through_rate > 1
