select
    rv.review_id,
    o.order_date,
    rv.review_date
from {{ ref('stg_reviews') }} as rv
inner join {{ ref('stg_orders') }} as o
    on rv.order_id = o.order_id
where rv.review_date < o.order_date
