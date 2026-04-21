with dataset_range as (
    select
        min(order_date) as min_order_date,
        max(order_date) as max_order_date
    from {{ ref('stg_orders') }}
),

product_sales as (
    select
        product_id,
        count(distinct order_id) as total_orders,
        sum(quantity) as total_units_sold,
        sum(line_net_revenue) as total_revenue,
        sum(line_cogs) as total_cogs,
        min(order_date) as first_sale_date,
        max(order_date) as last_sale_date,
        count(distinct date_trunc('month', order_date)) as active_months
    from {{ ref('int_order_line_enriched') }}
    group by 1
),

product_returns as (
    select
        product_id,
        sum(return_quantity) as return_units,
        sum(refund_amount) as refund_amount,
        count(*) as return_records
    from {{ ref('stg_returns') }}
    group by 1
),

product_inventory as (
    select
        product_id,
        avg(sell_through_rate) as avg_sell_through_rate,
        sum(stockout_days) as total_stockout_days,
        sum(stockout_flag) as stockout_months,
        sum(overstock_flag) as overstock_months,
        sum(reorder_flag) as reorder_months,
        count(distinct snapshot_date) as months_in_inventory
    from {{ ref('stg_inventory') }}
    group by 1
),

enriched as (
    select
        p.product_id,
        p.product_name,
        p.category,
        p.segment,
        p.size,
        p.color,
        p.price as list_price,
        p.cogs as unit_cogs,
        p.gross_margin_rate as list_margin_rate,
        coalesce(ps.total_orders, 0) as total_orders,
        coalesce(ps.total_units_sold, 0) as total_units_sold,
        coalesce(ps.total_revenue, 0) as total_revenue,
        coalesce(ps.total_cogs, 0) as total_cogs,
        coalesce(ps.total_revenue, 0) - coalesce(ps.total_cogs, 0) as gross_profit,
        case
            when coalesce(ps.total_revenue, 0) = 0 then null
            else cast(coalesce(ps.total_revenue, 0) - coalesce(ps.total_cogs, 0) as double)
                 / ps.total_revenue
        end as realized_margin_rate,
        ps.first_sale_date,
        ps.last_sale_date,
        ps.active_months,
        coalesce(pr.return_units, 0) as return_units,
        coalesce(pr.return_records, 0) as return_records,
        coalesce(pr.refund_amount, 0) as refund_amount,
        cast(coalesce(pr.return_units, 0) as double) / nullif(ps.total_units_sold, 0)
            as return_unit_rate,
        cast(coalesce(ps.total_revenue, 0) as double) / nullif(ps.total_units_sold, 0)
            as avg_selling_price,
        pi.avg_sell_through_rate,
        coalesce(pi.total_stockout_days, 0) as total_stockout_days,
        coalesce(pi.stockout_months, 0) as stockout_months,
        coalesce(pi.overstock_months, 0) as overstock_months,
        coalesce(pi.reorder_months, 0) as reorder_months,
        coalesce(pi.months_in_inventory, 0) as months_in_inventory,
        case
            when ps.product_id is null then 'never_sold'
            when ps.last_sale_date >= date_trunc('month', d.max_order_date) - interval '5 months'
                then 'active'
            when ps.last_sale_date >= date_trunc('month', d.max_order_date) - interval '11 months'
                then 'dormant'
            else 'discontinued'
        end as lifecycle_stage
    from {{ ref('stg_products') }} as p
    left join product_sales as ps
        on p.product_id = ps.product_id
    left join product_returns as pr
        on p.product_id = pr.product_id
    left join product_inventory as pi
        on p.product_id = pi.product_id
    cross join dataset_range as d
)

select
    e.*,
    row_number() over (partition by e.category order by e.total_revenue desc)
        as category_revenue_rank,
    row_number() over (partition by e.category order by e.gross_profit desc)
        as category_profit_rank,
    cast(e.total_revenue as double) / nullif(sum(e.total_revenue) over (partition by e.category), 0)
        as revenue_share_in_category
from enriched as e
order by e.total_revenue desc
