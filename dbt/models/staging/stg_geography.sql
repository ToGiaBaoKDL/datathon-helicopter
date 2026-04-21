select
    cast(zip as bigint) as zip,
    trim(city) as city,
    trim(region) as region,
    trim(district) as district
from {{ source('raw', 'geography') }}
