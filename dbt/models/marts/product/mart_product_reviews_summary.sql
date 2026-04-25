-- Product-level review aggregation joined with lifetime performance.
-- Grain: product_id.

with review_agg as (
    select
        product_id,
        count(*) as review_count,
        avg(rating) as avg_rating,
        sum(case when rating <= 2 then 1 else 0 end) as low_rating_count,
        cast(sum(case when rating <= 2 then 1 else 0 end) as double) / nullif(count(*), 0)
            as low_rating_rate
    from {{ ref('stg_reviews') }}
    group by 1
)

select
    p.product_id,
    p.product_name,
    p.category,
    p.segment,
    p.lifecycle_stage,
    p.total_revenue,
    p.total_units_sold,
    p.return_unit_rate,
    p.realized_margin_rate,
    coalesce(r.review_count, 0) as review_count,
    r.avg_rating,
    coalesce(r.low_rating_count, 0) as low_rating_count,
    r.low_rating_rate
from {{ ref('mart_product_lifetime_performance') }} as p
left join review_agg as r
    on p.product_id = r.product_id
order by p.total_revenue desc
