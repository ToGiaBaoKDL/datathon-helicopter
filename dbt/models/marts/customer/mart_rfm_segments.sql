-- RFM segmentation built on top of mart_customer_rfm.
-- Grain: customer_id.
-- R_score: 1 = most recent, 5 = least recent (recency is good).
-- F_score: 1 = lowest frequency, 5 = highest frequency.
-- M_score: 1 = lowest monetary, 5 = highest monetary.

with rfm_base as (
    select
        customer_id,
        acquisition_channel,
        age_group,
        total_orders,
        total_revenue,
        recency_days,
        avg_days_between_orders
    from {{ ref('mart_customer_rfm') }}
),

scored as (
    select
        customer_id,
        acquisition_channel,
        age_group,
        total_orders,
        total_revenue,
        recency_days,
        avg_days_between_orders,
        ntile(5) over (order by recency_days asc) as r_score,
        ntile(5) over (order by total_orders asc) as f_score,
        ntile(5) over (order by total_revenue asc) as m_score
    from rfm_base
),

segmented as (
    select
        customer_id,
        acquisition_channel,
        age_group,
        total_orders,
        total_revenue,
        recency_days,
        avg_days_between_orders,
        r_score,
        f_score,
        m_score,
        case
            when r_score >= 4 and f_score >= 4 and m_score >= 4 then 'Champions'
            when r_score >= 3 and f_score >= 3 and m_score >= 3 then 'Loyal'
            when r_score >= 4 and f_score <= 2 then 'New Customers'
            when r_score >= 3 and f_score <= 2 and m_score >= 3 then 'Potential Loyalist'
            when r_score >= 3 and f_score <= 2 and m_score <= 2 then 'Promising'
            when r_score <= 2 and f_score >= 3 then 'At Risk'
            when r_score <= 2 and f_score <= 2 and m_score >= 3 then 'Cannot Lose Them'
            when r_score <= 2 and f_score <= 2 and m_score <= 2 then 'Hibernating'
            when r_score >= 3 and f_score >= 3 and m_score <= 2 then 'Need Attention'
            else 'Others'
        end as rfm_segment
    from scored
)

select * from segmented
order by customer_id
