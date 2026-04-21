select
    s.order_id,
    o.order_date,
    s.ship_date,
    s.delivery_date
from {{ ref('stg_shipments') }} as s
inner join {{ ref('stg_orders') }} as o
    on s.order_id = o.order_id
where s.ship_date < o.order_date
   or s.delivery_date < s.ship_date
