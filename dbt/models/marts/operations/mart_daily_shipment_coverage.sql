-- Shipment data quality gap analysis.
-- Highlights the share of orders by status that lack shipment records.
-- Grain: (sales_date, order_status).

with order_daily as (
    select
        order_date as sales_date,
        order_status,
        count(*) as total_orders
    from {{ ref('stg_orders') }}
    group by 1, 2
),

shipped_orders as (
    select
        o.order_date as sales_date,
        o.order_status,
        count(*) as orders_with_shipment
    from {{ ref('stg_orders') }} as o
    inner join {{ ref('stg_shipments') }} as s
        on o.order_id = s.order_id
    group by 1, 2
)

select
    o.sales_date,
    o.order_status,
    o.total_orders,
    coalesce(s.orders_with_shipment, 0) as orders_with_shipment,
    o.total_orders - coalesce(s.orders_with_shipment, 0) as orders_without_shipment,
    cast(coalesce(s.orders_with_shipment, 0) as double)
        / nullif(o.total_orders, 0) as shipment_coverage_rate
from order_daily as o
left join shipped_orders as s
    on o.sales_date = s.sales_date
    and o.order_status = s.order_status
order by o.sales_date, o.order_status
