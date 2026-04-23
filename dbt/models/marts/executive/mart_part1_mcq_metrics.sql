with inter_order_gap as (
    select
        customer_id,
        order_date,
        datediff('day', lag(order_date) over (partition by customer_id order by order_date), order_date) as gap_days
    from {{ ref('stg_orders') }}
),

customer_order_counts as (
    select
        customer_id,
        count(*) as order_count
    from {{ ref('stg_orders') }}
    group by 1
),

segment_margin as (
    select
        segment,
        avg(gross_margin_rate) as avg_gross_margin_rate
    from {{ ref('stg_products') }}
    group by 1
),

streetwear_returns as (
    select
        r.return_reason,
        count(*) as return_count
    from {{ ref('stg_returns') }} as r
    inner join {{ ref('stg_products') }} as p
        on r.product_id = p.product_id
    where p.category = 'Streetwear'
    group by 1
),

bounce_by_source as (
    select
        traffic_source,
        avg(bounce_rate) as avg_bounce_rate
    from {{ ref('stg_web_traffic') }}
    group by 1
),

promo_line_share as (
    select
        sum(case when promo_id is not null then 1 else 0 end) as promo_lines,
        count(*) as total_lines
    from {{ ref('stg_order_items') }}
),

orders_per_customer_age_group as (
    select
        c.age_group,
        count(distinct o.order_id) as total_orders,
        count(distinct c.customer_id) as total_customers,
        cast(count(distinct o.order_id) as double) / nullif(count(distinct c.customer_id), 0) as avg_orders_per_customer
    from {{ ref('stg_customers') }} as c
    inner join {{ ref('stg_orders') }} as o
        on c.customer_id = o.customer_id
    where c.age_group is not null
    group by 1
),

revenue_by_region as (
    select
        region,
        sum(line_net_revenue) as total_revenue
    from {{ ref('int_order_line_enriched') }}
    where region is not null
    group by 1
),

cancelled_payment_mode as (
    select
        payment_method,
        count(*) as cancelled_order_count
    from {{ ref('stg_orders') }}
    where order_status = 'cancelled'
    group by 1
),

return_rate_by_size as (
    with return_counts as (
        select
            p.size,
            count(*) as return_count
        from {{ ref('stg_returns') }} as r
        inner join {{ ref('stg_products') }} as p
            on r.product_id = p.product_id
        group by 1
    ),
    size_sales as (
        select
            p.size,
            sum(oi.quantity) as sold_units
        from {{ ref('stg_order_items') }} as oi
        inner join {{ ref('stg_products') }} as p
            on oi.product_id = p.product_id
        group by 1
    )
    select
        ss.size,
        coalesce(rc.return_count, 0) as return_count,
        coalesce(ru.return_units, 0) as return_units,
        ss.sold_units,
        cast(coalesce(rc.return_count, 0) as double) / nullif(ss.sold_units, 0) as return_rate
    from size_sales as ss
    left join return_counts as rc
        on ss.size = rc.size
    left join (
        select
            p.size,
            sum(r.return_quantity) as return_units
        from {{ ref('stg_returns') }} as r
        inner join {{ ref('stg_products') }} as p
            on r.product_id = p.product_id
        group by 1
    ) as ru
        on ss.size = ru.size
),

payment_value_by_installments as (
    select
        installments,
        avg(payment_value) as avg_payment_value
    from {{ ref('stg_payments') }}
    group by 1
),

q1 as (
    select
        'q1_median_inter_order_gap_days' as metric_key,
        cast(median(gap_days) as double) as metric_value
    from inter_order_gap
    where customer_id in (
        select customer_id from customer_order_counts where order_count > 1
    )
      and gap_days is not null
),
q2 as (
    select
        'q2_top_segment_avg_margin' as metric_key,
        max(avg_gross_margin_rate) as metric_value
    from segment_margin
),
q3 as (
    select
        'q3_top_streetwear_return_reason_count' as metric_key,
        max(return_count) as metric_value
    from streetwear_returns
),
q4 as (
    select
        'q4_lowest_avg_bounce_rate' as metric_key,
        min(avg_bounce_rate) as metric_value
    from bounce_by_source
),
q5 as (
    select
        'q5_promo_line_percentage' as metric_key,
        cast(promo_lines as double) / nullif(total_lines, 0) as metric_value
    from promo_line_share
),
q6 as (
    select
        'q6_top_age_group_avg_orders_per_customer' as metric_key,
        max(avg_orders_per_customer) as metric_value
    from orders_per_customer_age_group
),
q7 as (
    select
        'q7_top_region_total_revenue' as metric_key,
        max(total_revenue) as metric_value
    from revenue_by_region
),
q8 as (
    select
        'q8_top_cancelled_payment_method_count' as metric_key,
        max(cancelled_order_count) as metric_value
    from cancelled_payment_mode
),
q9 as (
    select
        'q9_highest_return_rate_by_size' as metric_key,
        max(return_rate) as metric_value
    from return_rate_by_size
),
q10 as (
    select
        'q10_highest_avg_payment_value_by_installments' as metric_key,
        max(avg_payment_value) as metric_value
    from payment_value_by_installments
)

select * from q1
union all select * from q2
union all select * from q3
union all select * from q4
union all select * from q5
union all select * from q6
union all select * from q7
union all select * from q8
union all select * from q9
union all select * from q10
