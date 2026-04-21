with monthly_sales as (
    select
        product_id,
        date_trunc('month', order_date) as month_start_date,
        count(distinct order_id) as orders,
        sum(quantity) as units_sold,
        sum(line_net_revenue) as revenue,
        sum(line_cogs) as cogs
    from {{ ref('int_order_line_enriched') }}
    group by 1, 2
),

monthly_returns as (
    select
        product_id,
        date_trunc('month', return_date) as month_start_date,
        sum(return_quantity) as return_units,
        count(*) as return_records
    from {{ ref('stg_returns') }}
    group by 1, 2
),

monthly_inventory as (
    select
        product_id,
        date_trunc('month', snapshot_date) as month_start_date,
        stock_on_hand,
        units_received,
        units_sold as inventory_units_sold,
        stockout_days,
        days_of_supply,
        fill_rate,
        sell_through_rate,
        stockout_flag,
        overstock_flag,
        reorder_flag
    from {{ ref('stg_inventory') }}
)

select
    coalesce(s.product_id, i.product_id) as product_id,
    coalesce(s.month_start_date, i.month_start_date) as month_start_date,
    coalesce(s.orders, 0) as orders,
    coalesce(s.units_sold, 0) as units_sold,
    coalesce(s.revenue, 0) as revenue,
    coalesce(s.cogs, 0) as cogs,
    coalesce(s.revenue, 0) - coalesce(s.cogs, 0) as gross_profit,
    coalesce(r.return_units, 0) as return_units,
    coalesce(r.return_records, 0) as return_records,
    cast(coalesce(r.return_units, 0) as double) / nullif(s.units_sold, 0)
        as return_unit_rate,
    i.stock_on_hand,
    i.units_received,
    i.inventory_units_sold,
    i.stockout_days,
    i.days_of_supply,
    i.fill_rate,
    i.sell_through_rate,
    i.stockout_flag,
    i.overstock_flag,
    i.reorder_flag
from monthly_sales as s
full outer join monthly_inventory as i
    on s.product_id = i.product_id
    and s.month_start_date = i.month_start_date
left join monthly_returns as r
    on coalesce(s.product_id, i.product_id) = r.product_id
    and coalesce(s.month_start_date, i.month_start_date) = r.month_start_date
order by 1, 2
