with promo_lines as (
    select
        oi.promo_id,
        oi.order_id,
        oi.quantity,
        (oi.quantity * oi.unit_price) as line_net_revenue,
        oi.discount_amount,
        (oi.quantity * oi.unit_price + oi.discount_amount) as line_gross_revenue
    from {{ ref('stg_order_items') }} as oi
    where oi.promo_id is not null
),

promo_agg as (
    select
        promo_id,
        count(*) as total_order_lines,
        count(distinct order_id) as total_orders,
        sum(quantity) as total_units,
        sum(line_gross_revenue) as total_gross_revenue,
        sum(line_net_revenue) as total_net_revenue,
        sum(discount_amount) as total_discount_amount,
        avg(discount_amount) as avg_discount_per_line
    from promo_lines
    group by 1
)

select
    p.promo_id,
    p.promo_name,
    p.promo_type,
    p.discount_value,
    p.start_date,
    p.end_date,
    p.applicable_category,
    p.promo_channel,
    p.stackable_flag,
    p.min_order_value,
    coalesce(pa.total_order_lines, 0) as total_order_lines,
    coalesce(pa.total_orders, 0) as total_orders,
    coalesce(pa.total_units, 0) as total_units,
    coalesce(pa.total_gross_revenue, 0) as total_gross_revenue,
    coalesce(pa.total_net_revenue, 0) as total_net_revenue,
    coalesce(pa.total_discount_amount, 0) as total_discount_amount,
    pa.avg_discount_per_line,
    cast(coalesce(pa.total_net_revenue, 0) as double) / nullif(pa.total_orders, 0)
        as avg_order_value,
    cast(coalesce(pa.total_discount_amount, 0) as double) / nullif(pa.total_gross_revenue, 0)
        as discount_rate
from {{ ref('stg_promotions') }} as p
left join promo_agg as pa
    on p.promo_id = pa.promo_id
order by p.start_date
