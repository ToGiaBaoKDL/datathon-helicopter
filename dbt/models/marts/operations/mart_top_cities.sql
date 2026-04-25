-- Top cities by revenue and customer count.
-- Grain: (city, region) limited to top 20 by revenue.
-- Enables city-level drill-down within regions.

select
    g.city,
    g.region,
    count(distinct o.order_id) as orders,
    count(distinct o.customer_id) as customers,
    sum(ol.line_net_revenue) as revenue
from {{ ref('stg_orders') }} as o
inner join {{ ref('int_order_line_enriched') }} as ol
    on o.order_id = ol.order_id
inner join {{ ref('stg_geography') }} as g
    on o.zip = g.zip
group by 1, 2
order by revenue desc
limit 20
