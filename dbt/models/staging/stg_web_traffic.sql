select
    try_cast(date as date) as traffic_date,
    cast(sessions as double) as sessions,
    cast(unique_visitors as double) as unique_visitors,
    cast(page_views as double) as page_views,
    cast(bounce_rate as double) as bounce_rate,
    cast(avg_session_duration_sec as double) as avg_session_duration_sec,
    lower(trim(cast(traffic_source as varchar))) as traffic_source
from {{ source('raw', 'web_traffic') }}
