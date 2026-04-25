-- Daily payment mix and checkout performance KPIs.
-- Grain: (sales_date, payment_method).

with order_payment as (
    select
        order_date as sales_date,
        coalesce(order_payment_method, 'unknown') as payment_method,
        count(distinct order_id) as order_count,
        count(*) as order_line_count,
        sum(line_net_revenue) as revenue,
        sum(line_cogs) as cogs,
        sum(case when order_status = 'cancelled' then 1 else 0 end) as cancelled_lines,
        cast(sum(case when order_status = 'cancelled' then 1 else 0 end) as double)
            / nullif(count(*), 0) as cancellation_rate
    from {{ ref('int_order_line_enriched') }}
    group by 1, 2
),

payment_value as (
    select
        o.order_date as sales_date,
        coalesce(p.payment_method, 'unknown') as payment_method,
        avg(p.payment_value) as avg_payment_value,
        avg(p.installments) as avg_installments,
        sum(case when p.installments > 1 then 1 else 0 end) as installment_orders,
        cast(sum(case when p.installments > 1 then 1 else 0 end) as double)
            / nullif(count(*), 0) as installment_share
    from {{ ref('stg_payments') }} as p
    inner join {{ ref('stg_orders') }} as o
        on p.order_id = o.order_id
    group by 1, 2
)

select
    op.sales_date,
    op.payment_method,
    op.order_count,
    op.order_line_count,
    op.revenue,
    op.revenue - op.cogs as gross_profit,
    cast(op.revenue - op.cogs as double) / nullif(op.revenue, 0) as gross_margin_rate,
    cast(op.revenue as double) / nullif(op.order_count, 0) as avg_order_value,
    op.cancelled_lines,
    op.cancellation_rate,
    pv.avg_payment_value,
    pv.avg_installments,
    pv.installment_orders,
    pv.installment_share
from order_payment as op
left join payment_value as pv
    on op.sales_date = pv.sales_date
    and op.payment_method = pv.payment_method
order by op.sales_date, op.payment_method
