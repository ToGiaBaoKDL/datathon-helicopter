-- Regional category revenue matrix.
-- Grain: (region, category).
-- Enables heatmap of category preferences across regions.

select
    g.region,
    p.category,
    count(distinct o.order_id) as orders,
    sum(ol.line_net_revenue) as revenue,
    sum(ol.quantity) as units_sold
from {{ ref('stg_orders') }} as o
inner join {{ ref('int_order_line_enriched') }} as ol
    on o.order_id = ol.order_id
inner join {{ ref('stg_geography') }} as g
    on o.zip = g.zip
inner join {{ ref('stg_products') }} as p
    on ol.product_id = p.product_id
group by 1, 2
order by g.region, revenue desc
