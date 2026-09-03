{{ config(materialized='table', contract={'enforced': true}) }}

-- The API names a plant only by its code, so the dimension is what the facts
-- themselves reveal about it: when it first appeared and when it last did.

select
    resource_code,
    min(tx_date) as first_seen,
    max(tx_date) as last_seen,
    -- count returns bigint; the contract declares the range this column actually has.
    cast(count(distinct tx_date) as integer) as days_present
from {{ ref('stg_xm_hourly') }}
where entity = 'Recurso'
group by resource_code
