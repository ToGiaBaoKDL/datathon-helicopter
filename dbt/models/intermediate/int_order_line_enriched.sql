with order_lines as (
    select
        oi.order_id,
        oi.product_id,
        oi.quantity,
        oi.unit_price,
        oi.discount_amount,
        oi.promo_id,
        oi.promo_id_2,
        o.order_date,
        o.customer_id,
        o.zip,
        o.order_status,
        o.payment_method as order_payment_method,
        o.device_type,
        o.order_source,
        p.category,
        p.segment,
        p.size,
        p.color,
        p.price as list_price,
        p.cogs as unit_cogs
    from {{ ref('stg_order_items') }} as oi
    inner join {{ ref('stg_orders') }} as o
        on oi.order_id = o.order_id
    inner join {{ ref('stg_products') }} as p
        on oi.product_id = p.product_id
),

payments as (
    select
        order_id,
        payment_method as payment_method_paid,
        payment_value,
        installments
    from {{ ref('stg_payments') }}
),

customers as (
    select
        customer_id,
        city as customer_city,
        age_group,
        acquisition_channel
    from {{ ref('stg_customers') }}
),

geo as (
    select
        zip,
        city as shipping_city,
        region,
        district
    from {{ ref('stg_geography') }}
)

select
    ol.order_id,
    ol.product_id,
    ol.order_date,
    ol.customer_id,
    ol.zip,
    ol.order_status,
    ol.order_payment_method,
    p.payment_method_paid,
    p.payment_value,
    p.installments,
    ol.device_type,
    ol.order_source,
    c.customer_city,
    c.age_group,
    c.acquisition_channel,
    g.shipping_city,
    g.region,
    g.district,
    ol.category,
    ol.segment,
    ol.size,
    ol.color,
    ol.quantity,
    ol.list_price,
    ol.unit_price,
    ol.unit_cogs,
    ol.discount_amount,
    ol.promo_id,
    ol.promo_id_2,
    (ol.quantity * ol.list_price) as line_list_revenue,
    (ol.quantity * ol.unit_price) as line_net_revenue,
    (ol.quantity * ol.unit_cogs) as line_cogs,
    ((ol.quantity * ol.unit_price) - (ol.quantity * ol.unit_cogs)) as line_gross_profit
from order_lines as ol
left join payments as p
    on ol.order_id = p.order_id
left join customers as c
    on ol.customer_id = c.customer_id
left join geo as g
    on ol.zip = g.zip
