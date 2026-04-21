select
    product_id,
    month_start_date,
    count(*) as row_count
from {{ ref('mart_monthly_product_health') }}
group by 1, 2
having count(*) > 1
