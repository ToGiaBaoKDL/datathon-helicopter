with order_counts as (
    select
        order_id,
        count(*) as cnt
    from {{ ref('stg_orders') }}
    group by 1
),
payment_counts as (
    select
        order_id,
        count(*) as cnt
    from {{ ref('stg_payments') }}
    group by 1
)

select
    coalesce(o.order_id, p.order_id) as order_id,
    coalesce(o.cnt, 0) as order_count,
    coalesce(p.cnt, 0) as payment_count
from order_counts as o
full outer join payment_counts as p
    on o.order_id = p.order_id
where coalesce(o.cnt, 0) <> 1
   or coalesce(p.cnt, 0) <> 1
