-- Regional fulfillment and commercial profile.
-- Grain: region.

with region_orders as (
    select
        region,
        count(distinct order_id) as total_orders,
        count(distinct customer_id) as total_customers,
        sum(line_net_revenue) as total_revenue,
        sum(line_cogs) as total_cogs,
        sum(quantity) as total_units_sold
    from {{ ref('int_order_line_enriched') }}
    where region is not null
    group by 1
),

region_shipments as (
    select
        g.region,
        count(*) as shipped_orders,
        avg(datediff('day', o.order_date, s.ship_date)) as avg_days_to_ship,
        avg(datediff('day', o.order_date, s.delivery_date)) as avg_days_to_deliver,
        avg(s.shipping_fee) as avg_shipping_fee,
        sum(case when s.shipping_fee = 0 then 1 else 0 end) as free_shipping_orders
    from {{ ref('stg_shipments') }} as s
    inner join {{ ref('stg_orders') }} as o
        on s.order_id = o.order_id
    inner join {{ ref('stg_geography') }} as g
        on o.zip = g.zip
    group by 1
),

region_returns as (
    select
        g.region,
        sum(r.return_quantity) as return_units,
        sum(r.refund_amount) as refund_amount
    from {{ ref('stg_returns') }} as r
    inner join {{ ref('stg_orders') }} as o
        on r.order_id = o.order_id
    inner join {{ ref('stg_geography') }} as g
        on o.zip = g.zip
    group by 1
)

select
    ro.region,
    ro.total_orders,
    ro.total_customers,
    ro.total_revenue,
    ro.total_revenue - ro.total_cogs as gross_profit,
    cast(ro.total_revenue - ro.total_cogs as double) / nullif(ro.total_revenue, 0)
        as gross_margin_rate,
    ro.total_units_sold,
    coalesce(rs.shipped_orders, 0) as shipped_orders,
    rs.avg_days_to_ship,
    rs.avg_days_to_deliver,
    rs.avg_shipping_fee,
    coalesce(rs.free_shipping_orders, 0) as free_shipping_orders,
    cast(coalesce(rs.free_shipping_orders, 0) as double)
        / nullif(coalesce(rs.shipped_orders, 0), 0) as free_shipping_share,
    coalesce(rr.return_units, 0) as return_units,
    coalesce(rr.refund_amount, 0) as refund_amount,
    cast(coalesce(rr.return_units, 0) as double) / nullif(ro.total_units_sold, 0)
        as return_unit_rate
from region_orders as ro
left join region_shipments as rs
    on ro.region = rs.region
left join region_returns as rr
    on ro.region = rr.region
order by ro.total_revenue desc
