"""Tells Dagster about partitions that were loaded before it was watching.

The historical backfill ran through the loader directly, so the warehouse holds
the data and the asset graph has no record of it. Rather than fetch a decade
again to produce events Dagster would have written anyway, the partitions already
in the audit table are reported as materialised.

This exists for the one time the two got out of step. The schedule materialises
assets, so it does not need reconciling.
"""

from __future__ import annotations

import argparse
import logging

import dagster as dg
from dagster import DagsterInstance

from extract.config import SERIES
from extract.load import connect, coverage
from pipeline.assets import ASSET_KEY

log = logging.getLogger(__name__)


def report(instance: DagsterInstance, dry_run: bool = False) -> int:
    connection = connect()
    reported = 0
    try:
        for series in SERIES:
            for partition, rows in coverage(connection, series.key):
                key = dg.MultiPartitionKey(
                    {"month": partition.strftime("%Y-%m-%d"), "series": series.key}
                )
                if not dry_run:
                    instance.report_runless_asset_event(
                        dg.AssetMaterialization(
                            asset_key=ASSET_KEY,
                            partition=key,
                            description="Loaded before the asset graph was watching.",
                            metadata={"rows": rows, "reconciled": True},
                        )
                    )
                reported += 1
    finally:
        connection.close()

    log.info("%s %d partitions", "would report" if dry_run else "reported", reported)
    return reported


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    with DagsterInstance.get() as instance:
        print(report(instance, args.dry_run))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
