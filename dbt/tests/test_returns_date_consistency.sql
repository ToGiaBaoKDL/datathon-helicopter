select
    r.return_id,
    o.order_date,
    r.return_date
from {{ ref('stg_returns') }} as r
inner join {{ ref('stg_orders') }} as o
    on r.order_id = o.order_id
where r.return_date < o.order_date
