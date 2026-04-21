select
    cast(customer_id as bigint) as customer_id,
    cast(zip as bigint) as zip,
    trim(city) as city,
    try_cast(signup_date as date) as signup_date,
    nullif(trim(gender), '') as gender,
    nullif(trim(age_group), '') as age_group,
    nullif(trim(acquisition_channel), '') as acquisition_channel
from {{ source('raw', 'customers') }}
