-- The raw layer is owned by the loader rather than by dbt: dbt reads sources, it
-- does not create them. The statements are idempotent so a deploy can apply them
-- on every run without a migration history to keep in step.

CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.xm_hourly (
    metric_id      text        NOT NULL,
    entity         text        NOT NULL,
    resource_code  text        NOT NULL,
    tx_date        date        NOT NULL,
    -- The twenty four hours exactly as the API sent them. Unpivoting happens in
    -- the warehouse, so a change to the model never means fetching a decade again.
    hour_values    jsonb       NOT NULL,
    loaded_at      timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (metric_id, entity, resource_code, tx_date)
);

CREATE INDEX IF NOT EXISTS ix_xm_hourly_date ON raw.xm_hourly (tx_date);

-- One row per series and partition, so the coverage of a backfill is a query
-- rather than a guess.
CREATE TABLE IF NOT EXISTS raw.load_audit (
    series_key   text        NOT NULL,
    partition    date        NOT NULL,
    rows_loaded  integer     NOT NULL,
    source_rows  integer     NOT NULL,
    loaded_at    timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (series_key, partition)
);
