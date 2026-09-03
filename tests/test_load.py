"""Behaviour that depends on PostgreSQL, run in CI against a service container."""

from __future__ import annotations

from datetime import date

import pytest

from extract.config import BY_KEY
from extract.load import connect, coverage, ensure_schema, load
from extract.xm import Record

pytestmark = pytest.mark.postgres

SERIES = BY_KEY["precbolsnaci__sistema"]

# A month nothing else writes: not the loader, whose windows begin later, and not
# the CI fixture, which uses 2024-03. The assertions then count only what the test
# put there, whatever else the warehouse holds.
MONTH = date(2019, 7, 1)
NEXT_MONTH = date(2019, 8, 1)


def record(day: int, value: str = "10.5") -> Record:
    return Record(
        metric_id=SERIES.metric_id,
        entity=SERIES.entity,
        resource_code="Sistema",
        tx_date=MONTH.replace(day=day),
        values={"Hour01": value, "Hour02": "11.0"},
    )


@pytest.fixture
def connection():
    """Everything runs inside one transaction that is rolled back afterwards."""
    conn = connect()
    ensure_schema(conn)
    yield conn
    with conn.cursor() as cursor:
        cursor.execute(
            "DELETE FROM raw.xm_hourly WHERE tx_date >= %s AND tx_date < %s", (MONTH, NEXT_MONTH)
        )
        cursor.execute("DELETE FROM raw.load_audit WHERE partition = %s", (MONTH,))
    conn.commit()
    conn.close()


def rows_held(connection) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM raw.xm_hourly WHERE tx_date >= %s AND tx_date < %s",
            (MONTH, NEXT_MONTH),
        )
        return cursor.fetchone()[0]


def test_applying_the_schema_twice_is_harmless(connection):
    ensure_schema(connection)
    ensure_schema(connection)

    assert rows_held(connection) == 0


def test_a_partition_loaded_twice_holds_one_copy(connection):
    records = [record(1), record(2)]

    load(connection, SERIES, MONTH, records)
    load(connection, SERIES, MONTH, records)

    assert rows_held(connection) == 2


def test_reloading_replaces_what_the_source_now_says(connection):
    load(connection, SERIES, MONTH, [record(1, value="10.5")])
    load(connection, SERIES, MONTH, [record(1, value="99.9")])

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT hour_values ->> 'Hour01' FROM raw.xm_hourly WHERE tx_date = %s",
            (MONTH,),
        )
        assert cursor.fetchone()[0] == "99.9"


def test_the_audit_reports_what_a_partition_holds(connection):
    load(connection, SERIES, MONTH, [record(1), record(2)])

    assert (MONTH, 2) in coverage(connection, SERIES.key)


def test_an_empty_partition_is_still_recorded(connection):
    load(connection, SERIES, MONTH, [])

    # A month the source has nothing for is a fact worth keeping: without the row
    # a backfill would ask for it again on every run.
    assert (MONTH, 0) in coverage(connection, SERIES.key)

