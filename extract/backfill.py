"""Loads a range of partitions, skipping the ones already in hand.

The API answers one month per request, so a decade is a hundred and twenty of
them. A run that stops halfway leaves the partitions it finished recorded, and the
next run starts where it left off rather than from the beginning.
"""

from __future__ import annotations

import argparse
import logging
import time
from datetime import date, timedelta

from extract.config import BY_KEY, SERIES, Series
from extract.load import connect, coverage, ensure_schema, load
from extract.xm import SourceError, fetch_month

log = logging.getLogger(__name__)

# The API asks for nothing, but a hundred requests in a row deserves a pause.
PAUSE_SECONDS = 0.5


def months(first: date, last: date) -> list[date]:
    """Every month start from `first` to `last` inclusive."""
    current = first.replace(day=1)
    end = last.replace(day=1)
    out = []
    while current <= end:
        out.append(current)
        current = (current + timedelta(days=32)).replace(day=1)
    return out


def pending(loaded: set[date], wanted: list[date], force: bool) -> list[date]:
    return wanted if force else [month for month in wanted if month not in loaded]


def backfill(
    series: Series, first: date, last: date, force: bool = False, pause: float = PAUSE_SECONDS
) -> dict:
    connection = connect()
    ensure_schema(connection)

    loaded = {partition for partition, _ in coverage(connection, series.key)}
    wanted = months(max(first, series.start), last)
    todo = pending(loaded, wanted, force)

    log.info(
        "%s: %d partitions wanted, %d already loaded, %d to fetch",
        series.key, len(wanted), len(wanted) - len(todo), len(todo),
    )

    rows = 0
    failed: list[date] = []
    for index, month in enumerate(todo, start=1):
        try:
            rows += load(connection, series, month, fetch_month(series, month))
        except SourceError as error:
            # One month refusing is not a reason to abandon the other hundred.
            log.warning("%s", error)
            failed.append(month)
        if index < len(todo):
            time.sleep(pause)

    connection.close()
    return {"series": series.key, "fetched": len(todo), "rows": rows, "failed": failed}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--series", default="all", help="series key, or all")
    parser.add_argument("--start", required=True, help="first month, YYYY-MM")
    parser.add_argument("--end", required=True, help="last month, YYYY-MM")
    parser.add_argument("--force", action="store_true", help="reload partitions already held")
    args = parser.parse_args()

    first = date.fromisoformat(f"{args.start}-01")
    last = date.fromisoformat(f"{args.end}-01")
    chosen = SERIES if args.series == "all" else [BY_KEY[args.series]]

    for series in chosen:
        report = backfill(series, first, last, args.force)
        print(report)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
