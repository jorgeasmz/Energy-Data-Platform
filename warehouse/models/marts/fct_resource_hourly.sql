{{ config(materialized='table', contract={'enforced': true}) }}

-- One row per plant an hour. Fifty times the volume of the system grain, which
-- is why its window starts later than the system one.

select
    measured_at,
    tx_date as market_date,
    hour_of_day,
    resource_code,
    max(measurement) filter (where metric_id = 'PrecOferDesp') as offer_price,
    max(measurement) filter (where metric_id = 'EmisionesCO2Eq') as co2_equivalent
from {{ ref('stg_xm_hourly') }}
where entity = 'Recurso'
group by measured_at, tx_date, hour_of_day, resource_code
