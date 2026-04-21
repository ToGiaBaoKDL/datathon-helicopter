with line_facts as (
    select
        date_trunc('week', order_date) as week_start_date,
        region,
        order_id,
        customer_id,
        order_status,
        line_net_revenue,
        line_cogs,
        quantity,
        discount_amount
    from {{ ref('int_order_line_enriched') }}
    where region is not null
),
returns_weekly as (
    select
        date_trunc('week', r.return_date) as week_start_date,
        g.region,
        count(*) as return_record_count,
        sum(r.return_quantity) as return_units,
        sum(r.refund_amount) as refund_amount
    from {{ ref('stg_returns') }} as r
    inner join {{ ref('stg_orders') }} as o
        on r.order_id = o.order_id
    inner join {{ ref('stg_geography') }} as g
        on o.zip = g.zip
    group by 1, 2
)

select
    lf.week_start_date,
    lf.region,
    count(distinct lf.order_id) as order_count,
    count(distinct lf.customer_id) as active_customer_count,
    sum(lf.quantity) as sold_units,
    sum(lf.line_net_revenue) as gross_revenue,
    sum(lf.line_net_revenue - lf.line_cogs) as gross_profit,
    cast(sum(lf.line_net_revenue - lf.line_cogs) as double) / nullif(sum(lf.line_net_revenue), 0)
        as gross_margin_rate,
    sum(lf.discount_amount) as total_discount_amount,
    sum(case when lf.order_status = 'cancelled' then 1 else 0 end) as cancelled_line_count,
    max(coalesce(rw.return_record_count, 0)) as return_record_count,
    max(coalesce(rw.return_units, 0)) as return_units,
    max(coalesce(rw.refund_amount, 0)) as refund_amount
from line_facts as lf
left join returns_weekly as rw
    on lf.week_start_date = rw.week_start_date
   and lf.region = rw.region
group by 1, 2
