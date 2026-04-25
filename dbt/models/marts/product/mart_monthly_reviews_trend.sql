-- Monthly review volume and quality trend by product category.
-- Grain: (month_start_date, category).

with monthly_reviews as (
    select
        date_trunc('month', r.review_date) as month_start_date,
        p.category,
        count(*) as review_count,
        avg(r.rating) as avg_rating,
        sum(case when r.rating <= 2 then 1 else 0 end) as low_rating_count
    from {{ ref('stg_reviews') }} as r
    inner join {{ ref('stg_products') }} as p
        on r.product_id = p.product_id
    group by 1, 2
)

select
    month_start_date,
    category,
    review_count,
    avg_rating,
    low_rating_count,
    cast(low_rating_count as double) / nullif(review_count, 0) as low_rating_rate
from monthly_reviews
order by month_start_date, category
