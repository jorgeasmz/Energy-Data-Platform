"""The asset graph: one partitioned load, and the dbt models that read it."""

from datetime import date

import dagster as dg
from dagster import AssetExecutionContext
from dagster_dbt import DbtCliResource, dbt_assets

from extract.config import BY_KEY, SERIES, SYSTEM_START
from extract.load import connect, ensure_schema, load
from extract.xm import fetch_month
from pipeline.resources import dbt_project

# A calendar month is the largest span the API accepts in one request, so a
# partition is exactly one call. The series dimension keeps the six loads
# independent: one failing month does not hold up the others.
MONTHS = dg.MonthlyPartitionsDefinition(start_date=SYSTEM_START.strftime("%Y-%m-%d"))
SERIES_KEYS = dg.StaticPartitionsDefinition([series.key for series in SERIES])

LOAD_PARTITIONS = dg.MultiPartitionsDefinition({"month": MONTHS, "series": SERIES_KEYS})


def covers(series, month: date) -> bool:
    """Whether a series has anything to say about a month.

    The month dimension is shared by every series, but each starts when it starts,
    so the months before one begins are empty by definition rather than by failure.
    """
    return month >= series.start.replace(day=1)


@dg.asset(
    # The key the dbt source resolves to, which is what joins the two halves of
    # the graph into one lineage.
    key=["xm", "xm_hourly"],
    partitions_def=LOAD_PARTITIONS,
    group_name="extract",
    description="One month of one series, as the API returned it.",
)
def xm_hourly(context: AssetExecutionContext) -> dg.MaterializeResult:
    keys = context.partition_key.keys_by_dimension
    series = BY_KEY[keys["series"]]
    month = date.fromisoformat(keys["month"][:10])

    if not covers(series, month):
        context.log.info("%s starts at %s, nothing for %s", series.key, series.start, month)
        return dg.MaterializeResult(metadata={"rows": 0, "skipped": True})

    connection = connect()
    try:
        ensure_schema(connection)
        records = fetch_month(series, month)
        rows = load(connection, series, month, records)
    finally:
        connection.close()

    return dg.MaterializeResult(
        metadata={
            "rows": rows,
            "entities": len({record.resource_code for record in records}),
            "skipped": False,
        }
    )


@dbt_assets(manifest=dbt_project.manifest_path)
def warehouse_models(context: AssetExecutionContext, dbt: DbtCliResource):
    """Every dbt model, seed and test, as its own asset in the same graph."""
    yield from dbt.cli(["build"], context=context).stream()
