select
    rv.review_id,
    o.order_status
from {{ ref('stg_reviews') }} as rv
inner join {{ ref('stg_orders') }} as o
    on rv.order_id = o.order_id
where o.order_status <> 'delivered'
