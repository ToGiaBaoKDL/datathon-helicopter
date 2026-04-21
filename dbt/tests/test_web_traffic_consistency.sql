select
    traffic_date,
    sessions,
    unique_visitors,
    page_views,
    bounce_rate,
    avg_session_duration_sec
from {{ ref('stg_web_traffic') }}
where sessions < unique_visitors
   or page_views < sessions
   or bounce_rate < 0
   or bounce_rate > 1
   or avg_session_duration_sec < 0
