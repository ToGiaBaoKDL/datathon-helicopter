select
    month_start_date,
    category,
    segment,
    count(*) as row_count
from {{ ref('mart_monthly_category_performance') }}
group by 1, 2, 3
having count(*) > 1
