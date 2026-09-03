"""What is pulled from XM, and the shape of the source that decides how."""

from __future__ import annotations

import os
from datetime import date

# Public API of XM, the operator of the Colombian wholesale electricity market.
# No key and no account.
API_URL = os.getenv("XM_API_URL", "https://servapibi.xm.com.co/hourly")

# Measured against the API: a 30 day span returns 31 days of data, and 45 or 90
# return a non-JSON error. A calendar month never spans more than 30 days from its
# first to its last, which is why the partitions below are monthly.
MAX_SPAN_DAYS = 30

REQUEST_TIMEOUT = 60
MAX_ATTEMPTS = 4
BACKOFF_SECONDS = 2.0


class Series:
    """One metric at one granularity, with the date its history starts."""

    def __init__(self, metric_id: str, entity: str, start: date, description: str) -> None:
        self.metric_id = metric_id
        self.entity = entity
        self.start = start
        self.description = description

    @property
    def key(self) -> str:
        return f"{self.metric_id}__{self.entity}".lower()

    def __repr__(self) -> str:
        return f"Series({self.key})"


# System level series carry one value an hour, so a decade of them is small.
# Resource level series carry one value an hour per generating plant, which is
# fifty times the volume, and their window is bounded to fit the warehouse.
SYSTEM_START = date(2016, 1, 1)
RESOURCE_START = date(2024, 1, 1)

SERIES = [
    Series("PrecBolsNaci", "Sistema", SYSTEM_START, "Spot price of the national market"),
    Series("DemaReal", "Sistema", SYSTEM_START, "Real demand"),
    Series("DemaCome", "Sistema", SYSTEM_START, "Commercial demand"),
    Series("Gene", "Sistema", SYSTEM_START, "Generation"),
    Series("PrecOferDesp", "Recurso", RESOURCE_START, "Dispatch offer price per plant"),
    Series("EmisionesCO2Eq", "Recurso", RESOURCE_START, "CO2 equivalent emissions per plant"),
]

BY_KEY = {series.key: series for series in SERIES}
