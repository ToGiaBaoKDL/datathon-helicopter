select
    s.order_id,
    o.order_status
from {{ ref('stg_shipments') }} as s
inner join {{ ref('stg_orders') }} as o
    on s.order_id = o.order_id
where o.order_status not in ('shipped', 'delivered', 'returned')
