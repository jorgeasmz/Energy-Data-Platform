"""Writes what the API returned into the raw layer, once per partition.

A partition can be loaded any number of times. The primary key is the natural key
of the source, so a repeat replaces rather than duplicates, which is what lets a
backfill be interrupted and resumed without reasoning about what it got through.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import date
from pathlib import Path

import psycopg

from extract.config import Series
from extract.xm import Record, month_bounds

log = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "WAREHOUSE_URL", "postgresql://energy:energy@localhost:5435/energy"
)

SCHEMA_SQL = Path(__file__).resolve().parent.parent / "warehouse" / "sql" / "raw_schema.sql"

UPSERT = """
INSERT INTO raw.xm_hourly (metric_id, entity, resource_code, tx_date, hour_values, loaded_at)
VALUES (%s, %s, %s, %s, %s, now())
ON CONFLICT (metric_id, entity, resource_code, tx_date)
DO UPDATE SET hour_values = EXCLUDED.hour_values, loaded_at = now()
"""

AUDIT = """
INSERT INTO raw.load_audit (series_key, partition, rows_loaded, source_rows, loaded_at)
VALUES (%s, %s, %s, %s, now())
ON CONFLICT (series_key, partition)
DO UPDATE SET rows_loaded = EXCLUDED.rows_loaded,
              source_rows = EXCLUDED.source_rows,
              loaded_at = now()
"""


def connect(url: str = DATABASE_URL) -> psycopg.Connection:
    return psycopg.connect(url)


def ensure_schema(connection: psycopg.Connection) -> None:
    with connection.cursor() as cursor:
        cursor.execute(SCHEMA_SQL.read_text())
    connection.commit()


def load(
    connection: psycopg.Connection, series: Series, month: date, records: list[Record]
) -> int:
    """Stores one partition and records that it was stored."""
    first, _ = month_bounds(month)
    rows = [
        (r.metric_id, r.entity, r.resource_code, r.tx_date, json.dumps(r.values))
        for r in records
    ]

    with connection.cursor() as cursor:
        if rows:
            cursor.executemany(UPSERT, rows)
        cursor.execute(AUDIT, (series.key, first, len(rows), len(records)))
    connection.commit()

    log.info("%s %s: %d rows", series.key, first, len(rows))
    return len(rows)


def coverage(connection: psycopg.Connection, series_key: str) -> list[tuple[date, int]]:
    """Which partitions of a series are loaded, and how much each holds."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT partition, rows_loaded FROM raw.load_audit"
            " WHERE series_key = %s ORDER BY partition",
            (series_key,),
        )
        return cursor.fetchall()
