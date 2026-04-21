with order_lines as (
    select *
    from {{ ref('int_order_line_enriched') }}
),

daily_sales as (
    select
        order_date as sales_date,
        count(distinct order_id) as order_count,
        count(*) as order_line_count,
        sum(quantity) as units_sold,
        sum(line_net_revenue) as line_revenue,
        sum(line_cogs) as line_cogs,
        sum(discount_amount) as total_discount_amount,
        avg(line_net_revenue) as avg_line_revenue,
        sum(case when promo_id is not null then 1 else 0 end) as promo_line_count,
        sum(case when order_status = 'cancelled' then 1 else 0 end) as cancelled_line_count
    from order_lines
    group by 1
),

daily_returns as (
    select
        return_date as sales_date,
        count(*) as return_record_count,
        sum(return_quantity) as return_units,
        sum(refund_amount) as refund_amount_total
    from {{ ref('stg_returns') }}
    group by 1
),

daily_reviews as (
    select
        review_date as sales_date,
        count(*) as review_count,
        avg(rating) as avg_rating
    from {{ ref('stg_reviews') }}
    group by 1
),

daily_web as (
    select
        traffic_date as sales_date,
        sum(sessions) as sessions,
        sum(unique_visitors) as unique_visitors,
        sum(page_views) as page_views,
        avg(bounce_rate) as avg_bounce_rate,
        avg(avg_session_duration_sec) as avg_session_duration_sec
    from {{ ref('stg_web_traffic') }}
    group by 1
)

select
    ds.sales_date,
    ds.order_count,
    ds.order_line_count,
    ds.units_sold,
    ds.line_revenue,
    ds.line_cogs,
    ds.total_discount_amount,
    ds.avg_line_revenue,
    ds.promo_line_count,
    ds.cancelled_line_count,
    coalesce(dr.return_record_count, 0) as return_record_count,
    coalesce(dr.return_units, 0) as return_units,
    coalesce(dr.refund_amount_total, 0) as refund_amount_total,
    coalesce(rv.review_count, 0) as review_count,
    rv.avg_rating,
    dw.sessions,
    dw.unique_visitors,
    dw.page_views,
    dw.avg_bounce_rate,
    dw.avg_session_duration_sec
from daily_sales as ds
left join daily_returns as dr
    on ds.sales_date = dr.sales_date
left join daily_reviews as rv
    on ds.sales_date = rv.sales_date
left join daily_web as dw
    on ds.sales_date = dw.sales_date
