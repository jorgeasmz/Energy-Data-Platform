"""Client for the XM hourly API.

The source returns one record per date and entity, with the twenty four hours as
columns of a single object. Nothing is reshaped here: the loader stores what the
API returned and the warehouse does the transforming, so a change of mind about
the model never means fetching a decade again.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date, timedelta

import requests

from extract.config import (
    API_URL,
    BACKOFF_SECONDS,
    MAX_ATTEMPTS,
    MAX_SPAN_DAYS,
    REQUEST_TIMEOUT,
    Series,
)

log = logging.getLogger(__name__)


class SourceError(RuntimeError):
    """The API answered with something that is not a result."""


@dataclass(frozen=True)
class Record:
    """One entity on one date, with its hours still packed as the API sent them."""

    metric_id: str
    entity: str
    resource_code: str
    tx_date: date
    values: dict[str, str]


def month_bounds(month: date) -> tuple[date, date]:
    """First and last day of the month `month` falls in.

    A calendar month spans at most thirty days from first to last, which is the
    largest range the API accepts, so one partition is exactly one request.
    """
    first = month.replace(day=1)
    following = (first + timedelta(days=32)).replace(day=1)
    last = following - timedelta(days=1)
    if (last - first).days > MAX_SPAN_DAYS:
        raise ValueError(f"{first} to {last} exceeds the {MAX_SPAN_DAYS} day limit")
    return first, last


def parse(payload: dict, series: Series) -> list[Record]:
    items = payload.get("Items")
    if items is None:
        raise SourceError(f"no Items for {series.key}: {str(payload)[:200]}")

    records: list[Record] = []
    for item in items:
        day = date.fromisoformat(item["Date"][:10])
        for entity in item.get("HourlyEntities", []):
            values = dict(entity.get("Values", {}))
            code = values.pop("code", series.entity)
            records.append(
                Record(
                    metric_id=series.metric_id,
                    entity=series.entity,
                    resource_code=str(code),
                    tx_date=day,
                    values=values,
                )
            )
    return records


def fetch_month(series: Series, month: date, session: requests.Session | None = None) -> list[Record]:
    """Everything the API holds for one series in one month."""
    first, last = month_bounds(month)
    body = {
        "MetricId": series.metric_id,
        "StartDate": first.isoformat(),
        "EndDate": last.isoformat(),
        "Entity": series.entity,
    }
    caller = session or requests

    for attempt in range(1, MAX_ATTEMPTS + 1):
        response = caller.post(API_URL, json=body, timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            try:
                payload = response.json()
            except ValueError as error:
                # The API reports some failures as plain text with a 200.
                raise SourceError(f"{series.key} {first}: {response.text[:200]}") from error
            return parse(payload, series)

        if attempt == MAX_ATTEMPTS or response.status_code < 500:
            raise SourceError(f"{series.key} {first}: HTTP {response.status_code}")

        wait = BACKOFF_SECONDS * attempt
        log.warning("%s %s: HTTP %s, retrying in %.0fs", series.key, first, response.status_code, wait)
        time.sleep(wait)

    raise SourceError(f"{series.key} {first}: exhausted {MAX_ATTEMPTS} attempts")
