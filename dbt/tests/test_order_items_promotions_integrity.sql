with promo_1_missing as (
    select
        oi.order_id,
        oi.product_id,
        oi.promo_id as promo_key,
        'promo_id' as promo_field
    from {{ ref('stg_order_items') }} as oi
    left join {{ ref('stg_promotions') }} as p
        on oi.promo_id = p.promo_id
    where oi.promo_id is not null
      and p.promo_id is null
),
promo_2_missing as (
    select
        oi.order_id,
        oi.product_id,
        oi.promo_id_2 as promo_key,
        'promo_id_2' as promo_field
    from {{ ref('stg_order_items') }} as oi
    left join {{ ref('stg_promotions') }} as p
        on oi.promo_id_2 = p.promo_id
    where oi.promo_id_2 is not null
      and p.promo_id is null
)

select * from promo_1_missing
union all
select * from promo_2_missing
