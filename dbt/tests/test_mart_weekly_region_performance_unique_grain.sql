select
    week_start_date,
    region,
    count(*) as row_count
from {{ ref('mart_weekly_region_performance') }}
group by 1, 2
having count(*) > 1
