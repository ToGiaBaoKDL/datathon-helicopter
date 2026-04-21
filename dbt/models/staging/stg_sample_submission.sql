select
    try_cast(coalesce(date, "Date") as date) as sales_date,
    cast(coalesce(revenue, "Revenue") as double) as revenue,
    cast(coalesce(cogs, "COGS") as double) as cogs
from {{ source('raw', 'sample_submission') }}
