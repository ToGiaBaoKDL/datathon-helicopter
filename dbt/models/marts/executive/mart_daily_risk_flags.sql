with thresholds as (
    select
        quantile_cont(avg_stockout_days, 0.90) as p90_stockout_days,
        quantile_cont(return_record_rate, 0.95) as p95_return_rate,
        quantile_cont(session_to_order_rate, 0.10) as p10_conversion_rate
    from {{ ref('mart_daily_executive_kpis') }}
)

select
    e.sales_date,
    e.revenue,
    e.avg_stockout_days,
    e.return_record_rate,
    e.session_to_order_rate,
    case
        when e.avg_stockout_days > t.p90_stockout_days then 1
        else 0
    end as stockout_risk_flag,
    case
        when e.return_record_rate > t.p95_return_rate then 1
        else 0
    end as return_spike_flag,
    case
        when e.session_to_order_rate < t.p10_conversion_rate then 1
        else 0
    end as conversion_drop_flag
from {{ ref('mart_daily_executive_kpis') }} as e
 cross join thresholds as t
order by e.sales_date
