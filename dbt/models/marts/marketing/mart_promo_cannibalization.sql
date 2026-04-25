-- Promo cannibalization analysis: test whether promos pull forward demand.
-- Compares average daily revenue/orders in pre (-14..-1), during, and post (+1..+14) windows.
-- Grain: (promo_id, period_type).

with daily_revenue as (
    select
        sales_date,
        revenue,
        order_count
    from {{ ref('mart_forecast_daily_base') }}
),

promo_windows as (
    select
        p.promo_id,
        p.start_date,
        p.end_date,
        datediff('day', p.start_date, p.end_date) + 1 as campaign_days,
        p.start_date + interval '-14 days' as pre_start,
        p.start_date + interval '-1 days' as pre_end,
        p.end_date + interval '1 days' as post_start,
        p.end_date + interval '14 days' as post_end
    from {{ ref('stg_promotions') }} as p
),

pre_period as (
    select
        pw.promo_id,
        'pre' as period_type,
        avg(dr.revenue) as avg_daily_revenue,
        avg(dr.order_count) as avg_daily_orders,
        count(*) as days_in_period
    from promo_windows as pw
    inner join daily_revenue as dr
        on dr.sales_date between pw.pre_start and pw.pre_end
    group by pw.promo_id
),

during_period as (
    select
        pw.promo_id,
        'during' as period_type,
        avg(dr.revenue) as avg_daily_revenue,
        avg(dr.order_count) as avg_daily_orders,
        count(*) as days_in_period
    from promo_windows as pw
    inner join daily_revenue as dr
        on dr.sales_date between pw.start_date and pw.end_date
    group by pw.promo_id
),

post_period as (
    select
        pw.promo_id,
        'post' as period_type,
        avg(dr.revenue) as avg_daily_revenue,
        avg(dr.order_count) as avg_daily_orders,
        count(*) as days_in_period
    from promo_windows as pw
    inner join daily_revenue as dr
        on dr.sales_date between pw.post_start and pw.post_end
    group by pw.promo_id
),

unioned as (
    select * from pre_period
    union all
    select * from during_period
    union all
    select * from post_period
)

select
    u.promo_id,
    p.promo_name,
    p.promo_type,
    p.start_date,
    p.end_date,
    p.applicable_category,
    p.promo_channel,
    p.stackable_flag,
    u.period_type,
    u.avg_daily_revenue,
    u.avg_daily_orders,
    u.days_in_period
from unioned as u
inner join {{ ref('stg_promotions') }} as p
    on u.promo_id = p.promo_id
order by u.promo_id,
    case u.period_type
        when 'pre' then 1
        when 'during' then 2
        when 'post' then 3
    end
