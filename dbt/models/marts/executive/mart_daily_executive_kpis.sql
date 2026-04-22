with score as (
    select
        week_start_date,
        revenue as weekly_revenue,
        cogs as weekly_cogs,
        gross_profit as weekly_gross_profit,
        gross_margin_rate as weekly_gross_margin_rate,
        order_count as weekly_order_count,
        sessions as weekly_sessions,
        session_to_order_rate as weekly_session_to_order_rate,
        wow_revenue_growth_rate,
        wow_order_growth_rate,
        return_units as weekly_return_units,
        total_discount_amount as weekly_total_discount_amount,
        cancelled_line_count as weekly_cancelled_line_count
    from {{ ref('mart_weekly_business_scorecard') }}
),
daily as (
    select
        sales_date,
        revenue,
        cogs,
        order_count,
        sessions,
        unique_visitors,
        page_views,
        avg_bounce_rate,
        total_discount_amount,
        return_units,
        cancelled_line_count
    from {{ ref('mart_forecast_daily_base') }}
),
fulfillment as (
    select
        sales_date,
        avg_days_to_deliver,
        avg_days_to_ship,
        free_shipping_share,
        avg_shipping_fee
    from {{ ref('mart_daily_fulfillment_kpis') }}
),
inventory as (
    select
        sales_date,
        avg_stockout_days,
        avg_days_of_supply,
        avg_fill_rate,
        avg_sell_through_rate,
        stockout_product_count,
        overstock_product_count,
        reorder_product_count
    from {{ ref('mart_daily_inventory_kpis') }}
),
returns as (
    select
        sales_date,
        return_record_rate,
        return_unit_rate,
        refund_amount,
        late_delivery_return_count,
        defective_return_count,
        wrong_size_return_count
    from {{ ref('mart_daily_returns_kpis') }}
),
marketing as (
    select
        sales_date,
        purchasing_customer_count,
        session_to_order_rate,
        pages_per_session
    from {{ ref('mart_daily_marketing_kpis') }}
),
latest_inventory as (
    select
        sales_date,
        avg_stockout_days,
        avg_days_of_supply,
        avg_fill_rate,
        avg_sell_through_rate,
        stockout_product_count,
        overstock_product_count,
        reorder_product_count,
        lead(sales_date, 1) over (order by sales_date) as next_sales_date
    from inventory
),
joined as (
    select
        d.sales_date,
        date_trunc('week', d.sales_date) as week_start_date,
        d.revenue,
        d.cogs,
        d.revenue - d.cogs as gross_profit,
        cast(d.revenue - d.cogs as double) / nullif(d.revenue, 0) as gross_margin_rate,
        d.order_count,
        d.sessions,
        d.unique_visitors,
        d.page_views,
        d.avg_bounce_rate,
        d.total_discount_amount,
        d.return_units,
        d.cancelled_line_count,
        cast(d.order_count as double) / nullif(d.sessions, 0) as session_to_order_rate,
        cast(d.return_units as double) / nullif(d.order_count, 0) as returns_per_order,
        f.avg_days_to_deliver,
        f.avg_days_to_ship,
        f.free_shipping_share,
        f.avg_shipping_fee,
        li.avg_stockout_days,
        li.avg_days_of_supply,
        li.avg_fill_rate,
        li.avg_sell_through_rate,
        li.stockout_product_count,
        li.overstock_product_count,
        li.reorder_product_count,
        r.return_record_rate,
        r.return_unit_rate,
        r.refund_amount,
        r.late_delivery_return_count,
        r.defective_return_count,
        r.wrong_size_return_count,
        m.purchasing_customer_count,
        m.pages_per_session
    from daily as d
    left join fulfillment as f
        on d.sales_date = f.sales_date
    left join latest_inventory as li
        on d.sales_date >= li.sales_date
       and (d.sales_date < li.next_sales_date or li.next_sales_date is null)
    left join returns as r
        on d.sales_date = r.sales_date
    left join marketing as m
        on d.sales_date = m.sales_date
)

select
    j.*,
    s.weekly_revenue,
    s.weekly_cogs,
    s.weekly_gross_profit,
    s.weekly_gross_margin_rate,
    s.weekly_order_count,
    s.weekly_sessions,
    s.weekly_session_to_order_rate,
    s.wow_revenue_growth_rate,
    s.wow_order_growth_rate,
    s.weekly_return_units,
    s.weekly_total_discount_amount,
    s.weekly_cancelled_line_count
from joined as j
left join score as s
    on j.week_start_date = s.week_start_date
