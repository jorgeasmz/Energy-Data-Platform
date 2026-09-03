from __future__ import annotations

from datetime import date

from extract.config import BY_KEY
from pipeline.assets import LOAD_PARTITIONS, covers

RESOURCE = BY_KEY["precoferdesp__recurso"]
SYSTEM = BY_KEY["precbolsnaci__sistema"]


def test_a_month_before_a_series_begins_is_covered_by_nothing():
    assert covers(RESOURCE, date(2020, 5, 1)) is False


def test_the_month_a_series_begins_in_is_covered():
    assert covers(RESOURCE, RESOURCE.start.replace(day=1)) is True


def test_a_series_that_starts_earlier_covers_more():
    early = date(2016, 1, 1)

    assert covers(SYSTEM, early) is True
    assert covers(RESOURCE, early) is False


def test_the_load_is_partitioned_by_series_and_month():
    assert set(LOAD_PARTITIONS.partition_dimension_names) == {"month", "series"}
