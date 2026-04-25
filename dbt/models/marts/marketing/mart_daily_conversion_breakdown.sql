-- Daily conversion and order metrics broken down by device, payment method, and order source.
-- Note: web traffic is not segmented by device/source, so conversion rates are approximated
-- using total daily sessions as denominator. This is a directional metric, not exact.
-- Grain: (sales_date, breakdown_type, breakdown_value).

with daily_sessions as (
    select
        traffic_date as sales_date,
        sum(sessions) as total_sessions
    from {{ ref('stg_web_traffic') }}
    group by 1
),

by_device as (
    select
        order_date as sales_date,
        'device_type' as breakdown_type,
        coalesce(device_type, 'unknown') as breakdown_value,
        count(distinct order_id) as order_count,
        count(*) as order_line_count,
        sum(line_net_revenue) as revenue,
        sum(case when order_status = 'cancelled' then 1 else 0 end) as cancelled_lines
    from {{ ref('int_order_line_enriched') }}
    group by 1, 2, 3
),

by_payment as (
    select
        order_date as sales_date,
        'payment_method' as breakdown_type,
        coalesce(order_payment_method, 'unknown') as breakdown_value,
        count(distinct order_id) as order_count,
        count(*) as order_line_count,
        sum(line_net_revenue) as revenue,
        sum(case when order_status = 'cancelled' then 1 else 0 end) as cancelled_lines
    from {{ ref('int_order_line_enriched') }}
    group by 1, 2, 3
),

by_source as (
    select
        order_date as sales_date,
        'order_source' as breakdown_type,
        coalesce(order_source, 'unknown') as breakdown_value,
        count(distinct order_id) as order_count,
        count(*) as order_line_count,
        sum(line_net_revenue) as revenue,
        sum(case when order_status = 'cancelled' then 1 else 0 end) as cancelled_lines
    from {{ ref('int_order_line_enriched') }}
    group by 1, 2, 3
),

unioned as (
    select * from by_device
    union all
    select * from by_payment
    union all
    select * from by_source
)

select
    u.sales_date,
    u.breakdown_type,
    u.breakdown_value,
    u.order_count,
    u.order_line_count,
    u.revenue,
    cast(u.revenue as double) / nullif(u.order_count, 0) as avg_order_value,
    u.cancelled_lines,
    cast(u.cancelled_lines as double) / nullif(u.order_line_count, 0) as cancellation_rate,
    ds.total_sessions,
    cast(u.order_count as double) / nullif(ds.total_sessions, 0) as approx_conversion_rate
from unioned as u
left join daily_sessions as ds
    on u.sales_date = ds.sales_date
order by u.sales_date, u.breakdown_type, u.breakdown_value
