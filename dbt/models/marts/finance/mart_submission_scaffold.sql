select
    sales_date as date,
    revenue,
    cogs
from {{ ref('stg_sample_submission') }}
order by sales_date
