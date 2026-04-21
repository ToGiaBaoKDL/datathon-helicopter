with returns_daily as (
    select
        o.order_date as sales_date,
        count(*) as return_record_count,
        sum(r.return_quantity) as return_units,
        sum(r.refund_amount) as refund_amount,
        sum(case when r.return_reason = 'defective' then 1 else 0 end) as defective_return_count,
        sum(case when r.return_reason = 'wrong_size' then 1 else 0 end) as wrong_size_return_count,
        sum(case when r.return_reason = 'changed_mind' then 1 else 0 end) as changed_mind_return_count,
        sum(case when r.return_reason = 'not_as_described' then 1 else 0 end) as not_as_described_return_count,
        sum(case when r.return_reason = 'late_delivery' then 1 else 0 end) as late_delivery_return_count
    from {{ ref('stg_returns') }} as r
    inner join {{ ref('stg_orders') }} as o
        on r.order_id = o.order_id
    group by 1
),
order_lines_daily as (
    select
        o.order_date as sales_date,
        count(*) as order_line_count,
        sum(oi.quantity) as sold_units
    from {{ ref('stg_order_items') }} as oi
    inner join {{ ref('stg_orders') }} as o
        on oi.order_id = o.order_id
    group by 1
)

select
    old.sales_date,
    old.order_line_count,
    old.sold_units,
    coalesce(rd.return_record_count, 0) as return_record_count,
    coalesce(rd.return_units, 0) as return_units,
    coalesce(rd.refund_amount, 0) as refund_amount,
    cast(coalesce(rd.return_record_count, 0) as double) / nullif(old.order_line_count, 0)
        as return_record_rate,
    cast(coalesce(rd.return_units, 0) as double) / nullif(old.sold_units, 0)
        as return_unit_rate,
    coalesce(rd.defective_return_count, 0) as defective_return_count,
    coalesce(rd.wrong_size_return_count, 0) as wrong_size_return_count,
    coalesce(rd.changed_mind_return_count, 0) as changed_mind_return_count,
    coalesce(rd.not_as_described_return_count, 0) as not_as_described_return_count,
    coalesce(rd.late_delivery_return_count, 0) as late_delivery_return_count
from order_lines_daily as old
left join returns_daily as rd
    on old.sales_date = rd.sales_date
