with customer_first_order as (
    select
        customer_id,
        date_trunc('month', min(order_date)) as cohort_month
    from {{ ref('stg_orders') }}
    group by 1
),

cohort_size as (
    select
        cohort_month,
        count(*) as cohort_size
    from customer_first_order
    group by 1
),

monthly_activity as (
    select
        customer_id,
        date_trunc('month', order_date) as activity_month,
        count(distinct order_id) as orders,
        sum(line_net_revenue) as revenue,
        sum(line_cogs) as cogs
    from {{ ref('int_order_line_enriched') }}
    group by 1, 2
),

cohort_activity as (
    select
        cfo.cohort_month,
        datediff('month', cfo.cohort_month, ma.activity_month) as months_since_first_order,
        count(distinct ma.customer_id) as active_customer_count,
        sum(ma.orders) as total_orders,
        sum(ma.revenue) as total_revenue,
        sum(ma.cogs) as total_cogs
    from customer_first_order as cfo
    inner join monthly_activity as ma
        on cfo.customer_id = ma.customer_id
    group by 1, 2
)

select
    ca.cohort_month,
    ca.months_since_first_order,
    cs.cohort_size,
    ca.active_customer_count,
    cast(ca.active_customer_count as double) / nullif(cs.cohort_size, 0) as retention_rate,
    ca.total_orders,
    ca.total_revenue,
    ca.total_cogs,
    ca.total_revenue - ca.total_cogs as gross_profit,
    cast(ca.total_revenue as double) / nullif(ca.total_orders, 0) as avg_order_value
from cohort_activity as ca
inner join cohort_size as cs
    on ca.cohort_month = cs.cohort_month
order by 1, 2
