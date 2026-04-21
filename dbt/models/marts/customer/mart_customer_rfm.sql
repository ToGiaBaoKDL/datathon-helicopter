with customer_orders as (
    select
        customer_id,
        min(order_date) as first_order_date,
        max(order_date) as last_order_date,
        count(*) as total_orders
    from {{ ref('stg_orders') }}
    group by 1
),

customer_value as (
    select
        customer_id,
        sum(line_net_revenue) as total_revenue,
        sum(line_cogs) as total_cogs
    from {{ ref('int_order_line_enriched') }}
    group by 1
),

inter_order_gap as (
    select
        customer_id,
        datediff('day', lag(order_date) over (partition by customer_id order by order_date), order_date)
            as gap_days
    from {{ ref('stg_orders') }}
),

avg_gap as (
    select
        customer_id,
        avg(gap_days) as avg_days_between_orders
    from inter_order_gap
    where gap_days is not null
    group by 1
),

dataset_max_date as (
    select max(order_date) as max_order_date from {{ ref('stg_orders') }}
)

select
    co.customer_id,
    c.acquisition_channel,
    c.age_group,
    co.first_order_date,
    co.last_order_date,
    co.total_orders,
    cv.total_revenue,
    cv.total_cogs,
    cv.total_revenue - cv.total_cogs as gross_profit,
    cast(cv.total_revenue as double) / nullif(co.total_orders, 0) as avg_order_value,
    datediff('day', co.last_order_date, d.max_order_date) as recency_days,
    ag.avg_days_between_orders
from customer_orders as co
inner join customer_value as cv
    on co.customer_id = cv.customer_id
left join {{ ref('stg_customers') }} as c
    on co.customer_id = c.customer_id
left join avg_gap as ag
    on co.customer_id = ag.customer_id
cross join dataset_max_date as d
order by co.customer_id
