with shipments as (
    select
        s.order_id,
        o.order_date,
        s.ship_date,
        s.delivery_date,
        s.shipping_fee
    from {{ ref('stg_shipments') }} as s
    inner join {{ ref('stg_orders') }} as o
        on s.order_id = o.order_id
),
daily as (
    select
        order_date as sales_date,
        count(*) as shipped_order_count,
        avg(datediff('day', order_date, ship_date)) as avg_days_to_ship,
        avg(datediff('day', ship_date, delivery_date)) as avg_days_in_transit,
        avg(datediff('day', order_date, delivery_date)) as avg_days_to_deliver,
        sum(case when shipping_fee = 0 then 1 else 0 end) as free_shipping_order_count,
        avg(shipping_fee) as avg_shipping_fee,
        sum(shipping_fee) as total_shipping_fee
    from shipments
    group by 1
)

select
    sales_date,
    shipped_order_count,
    avg_days_to_ship,
    avg_days_in_transit,
    avg_days_to_deliver,
    free_shipping_order_count,
    cast(free_shipping_order_count as double) / nullif(shipped_order_count, 0)
        as free_shipping_share,
    avg_shipping_fee,
    total_shipping_fee
from daily
