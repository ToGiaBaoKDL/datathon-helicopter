with line_facts as (
    select
        date_trunc('month', order_date) as month_start_date,
        category,
        segment,
        order_status,
        order_id,
        quantity,
        line_net_revenue,
        line_cogs,
        discount_amount
    from {{ ref('int_order_line_enriched') }}
),
returns_monthly as (
    select
        date_trunc('month', o.order_date) as month_start_date,
        p.category,
        p.segment,
        count(*) as return_record_count,
        sum(r.return_quantity) as return_units,
        sum(r.refund_amount) as refund_amount
    from {{ ref('stg_returns') }} as r
    inner join {{ ref('stg_orders') }} as o
        on r.order_id = o.order_id
    inner join {{ ref('stg_products') }} as p
        on r.product_id = p.product_id
    group by 1, 2, 3
),
agg as (
    select
        month_start_date,
        category,
        segment,
        count(distinct order_id) as order_count,
        sum(quantity) as sold_units,
        sum(line_net_revenue) as gross_revenue,
        sum(discount_amount) as total_discount_amount,
        sum(line_net_revenue - line_cogs) as gross_profit,
        sum(case when order_status = 'cancelled' then line_net_revenue else 0 end) as cancelled_revenue
    from line_facts
    group by 1, 2, 3
)

select
    a.month_start_date,
    a.category,
    a.segment,
    a.order_count,
    a.sold_units,
    a.gross_revenue,
    a.total_discount_amount,
    a.gross_profit,
    cast(a.gross_profit as double) / nullif(a.gross_revenue, 0) as gross_margin_rate,
    a.cancelled_revenue,
    cast(a.cancelled_revenue as double) / nullif(a.gross_revenue, 0) as cancelled_revenue_share,
    coalesce(rm.return_record_count, 0) as return_record_count,
    coalesce(rm.return_units, 0) as return_units,
    coalesce(rm.refund_amount, 0) as refund_amount,
    cast(coalesce(rm.return_units, 0) as double) / nullif(a.sold_units, 0) as return_unit_rate
from agg as a
left join returns_monthly as rm
    on a.month_start_date = rm.month_start_date
   and a.category = rm.category
   and a.segment = rm.segment
