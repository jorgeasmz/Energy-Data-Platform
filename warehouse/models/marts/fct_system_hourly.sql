{{ config(materialized='table', contract={'enforced': true}) }}

-- One row an hour for the market as a whole, with each metric as its own column.
-- This is the grain another project consumes as a time series, so the four
-- measurements are aligned here rather than joined at read time.

select
    measured_at,
    tx_date as market_date,
    hour_of_day,
    max(measurement) filter (where metric_id = 'PrecBolsNaci') as spot_price,
    max(measurement) filter (where metric_id = 'DemaReal') as real_demand,
    max(measurement) filter (where metric_id = 'DemaCome') as commercial_demand,
    max(measurement) filter (where metric_id = 'Gene') as generation
from {{ ref('stg_xm_hourly') }}
where entity = 'Sistema'
group by measured_at, tx_date, hour_of_day
