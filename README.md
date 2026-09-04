# Energy Data Platform

Loads the Colombian wholesale electricity market from the public API of its
operator, and models it into a warehouse another project reads as a time series.

![CI](https://github.com/jorgeasmz/Energy-Data-Platform/actions/workflows/ci.yml/badge.svg)

## Source

XM operates the Colombian market and publishes an hourly API with no key and no
account. Its shape decides most of what follows.

| | |
|---|---|
| History | 2016 onward |
| Range per request | **30 days**, measured: 45 and 90 return a non-JSON error |
| Response | One record per date and entity, with the hours packed as `Hour01` to `Hour24` |
| Grains | Four series for the market as a whole, two per generating plant |

The two grains differ by a factor of fifty. A system series carries one value an
hour; a resource series carries one per plant, and 122 plants appear across the
loaded window. That is why the resource series start later than the system ones:
the window is set by what the warehouse can hold, and it is a configured date
rather than an accident.

## Partitioning

A partition is one series in one month, which is exactly one request. That is not
a convention: a calendar month never spans more than thirty days from its first
day to its last, which is the largest range the API accepts. The source's limit
is what sets the grain of the schedule.

The month dimension is shared by every series while each begins on its own date,
so a partition before a series starts materialises as empty rather than failing.

## Idempotency

The primary key of the raw table is the natural key of the source, and a load
upserts. A partition can be loaded any number of times and holds one copy:

```
first load:  1595 rows
second load: 1595 rows written, 1595 rows in the table
```

Every partition also writes a row to `raw.load_audit`, so the coverage of a
backfill is a query rather than a guess, and a run that stops halfway starts from
where it left off:

```
precbolsnaci__sistema: 3 partitions wanted, 3 already loaded, 0 to fetch
```

A month the source refuses does not abandon the other hundred. It is reported and
the run continues.

## Model

Nothing is reshaped on the way in. The raw layer holds what the API returned,
hours still packed, so a change of mind about the model never means fetching a
decade again.

```
raw.xm_hourly              as returned, twenty four hours in one JSON object
  └─ staging.stg_xm_hourly unpivoted: one row per metric, entity, date and hour
       ├─ marts.dim_resource        every plant, and the span it appears over
       ├─ marts.fct_system_hourly   one row an hour, four metrics as columns
       └─ marts.fct_resource_hourly one row per plant an hour
     marts.dim_series       the catalogue, with the names the API itself reports
```

`fct_system_hourly` is the grain another project consumes, so its four
measurements are aligned there rather than joined at read time.

## Contracts

The marts declare their columns and types, and dbt refuses to build a model whose
output does not match. That is not decoration: it caught a real mismatch on the
first build.

```
| column_name  | definition_type | contract_type | mismatch_reason    |
| days_present | LONGINTEGER     | INTEGER       | data type mismatch |
```

`count(distinct ...)` returns `bigint` in PostgreSQL. Without the contract the
column would have shipped as a type the documentation did not claim, and the
consumer would have found out.

Twenty four checks run on every build: uniqueness on each grain, a foreign key
from the resource facts to the plant dimension, ranges on the hour and on the
price, and freshness on the source.

## Orchestration

Six assets in one graph, spanning the Python that loads and the dbt that models.

```
xm/xm_hourly                     partitioned by series and month
  └─ staging/stg_xm_hourly
       ├─ marts/dim_resource
       ├─ marts/fct_system_hourly
       └─ marts/fct_resource_hourly
     marts/dim_series
```

The raw asset carries the key the dbt source resolves to, which is what joins the
two halves into one lineage rather than two disconnected graphs.

Dagster's daemon needs a process that runs continuously, and the free tier this is
deployed on offers none, so the schedule lives in GitHub Actions and invokes the
same assets. The code does not know the difference.

## Running it

```bash
docker compose up -d
python -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt

export DBT_PROFILES_DIR=warehouse
python -m extract.backfill --start 2026-06 --end 2026-08
dbt deps --project-dir warehouse
dbt build --project-dir warehouse
```

Three months of the six series is 12,858 raw rows and 8.7 MB, which becomes 2,208
hourly rows for the market and 250,584 for its plants.

The deployed warehouse holds the system series from 2016 and the resource series
from 2024, which is what the free tier the database runs on allows:

| | |
|---|---:|
| Database | 264 MB of 512 |
| Hours of the market | 93,504 |
| Rows per plant and hour | 2,601,552 |
| Plants | 135 |
| Range | 2016-01-01 to 2026-08-31 |

That window was chosen from a measurement rather than a guess. Three months of
every series cost 8 MB, almost all of it the resource grain, and the resource
series are what set the limit: a month of them is fifty times a month of the
system ones. The system history is a decade for 4 MB.

For the asset graph and the state of every partition:

```bash
export DAGSTER_HOME=$PWD/.dagster_home PYTHONPATH=.
dagster dev -m pipeline.definitions
```

## Development

```bash
dbt deps --project-dir warehouse
dbt parse --project-dir warehouse   # the asset graph reads the manifest on import

pytest                    # 19 tests, offline
pytest -m postgres        # 5 more, against a live warehouse
ruff check .
```

The manifest is a build artefact, not a file in the repository, and `pipeline.assets`
reads it when it is imported. Parsing needs the project and its packages but no
database, which is why it comes before the tests rather than with the build.

No test in the default run reaches the API or a database. The client is driven by
a fake session that returns what the real one returns, including the case the API
reports as plain text under a 200.

CI additionally loads a fixture of one day of every series and runs `dbt build`
against it, so the transformations are exercised on known values rather than only
parsed. That fixture truncates the raw tables and is meant for a fresh database.

## Project structure

```text
Energy-Data-Platform/
├── extract/
│   ├── config.py         # The series, their windows, and the source's limits
│   ├── xm.py             # API client, one month per request, with retries
│   ├── load.py           # Upsert into the raw layer, and the partition audit
│   └── backfill.py       # A range of partitions, skipping what is held
├── pipeline/
│   ├── assets.py         # The partitioned load and the dbt models as one graph
│   ├── resources.py      # The dbt project Dagster reads
│   └── definitions.py    # The code location
├── warehouse/
│   ├── models/           # staging and marts, with contracts and tests
│   ├── seeds/            # The series catalogue
│   ├── macros/           # Schema naming, so marts is called marts
│   └── sql/              # DDL of the raw layer, owned by the loader
└── tests/                # pytest suite, offline by default
```
