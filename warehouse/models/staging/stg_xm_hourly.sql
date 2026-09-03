{{ config(materialized='view') }}

-- The source packs a day into one object of twenty four keys. Unpivoting is the
-- first thing every model needs and the only thing this one does.

with source as (

    select * from {{ source('xm', 'xm_hourly') }}

),

unpivoted as (

    select
        source.metric_id,
        source.entity,
        source.resource_code,
        source.tx_date,
        -- 'Hour01' through 'Hour24'
        cast(substring(hours.key from 5) as integer) as hour_of_day,
        nullif(hours.value, '') as raw_value,
        source.loaded_at
    from source,
        lateral jsonb_each_text(source.hour_values) as hours(key, value)

)

select
    metric_id,
    entity,
    resource_code,
    tx_date,
    hour_of_day,
    -- Hour01 covers midnight to one, so the hour number is one ahead of the offset.
    tx_date + make_interval(hours => hour_of_day - 1) as measured_at,
    cast(raw_value as numeric) as measurement,
    loaded_at
from unpivoted
