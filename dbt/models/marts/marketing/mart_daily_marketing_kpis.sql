with web as (
    select
        traffic_date as sales_date,
        sessions,
        unique_visitors,
        page_views,
        bounce_rate,
        avg_session_duration_sec
    from {{ ref('stg_web_traffic') }}
),
orders as (
    select
        order_date as sales_date,
        count(distinct order_id) as order_count,
        count(distinct customer_id) as purchasing_customer_count
    from {{ ref('stg_orders') }}
    group by 1
)

select
    w.sales_date,
    w.sessions,
    w.unique_visitors,
    w.page_views,
    w.bounce_rate,
    w.avg_session_duration_sec,
    coalesce(o.order_count, 0) as order_count,
    coalesce(o.purchasing_customer_count, 0) as purchasing_customer_count,
    cast(coalesce(o.order_count, 0) as double) / nullif(w.sessions, 0) as session_to_order_rate,
    cast(w.page_views as double) / nullif(w.sessions, 0) as pages_per_session
from web as w
left join orders as o
    on w.sales_date = o.sales_date
