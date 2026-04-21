select
    r.return_id,
    o.order_status
from {{ ref('stg_returns') }} as r
inner join {{ ref('stg_orders') }} as o
    on r.order_id = o.order_id
where o.order_status <> 'returned'
