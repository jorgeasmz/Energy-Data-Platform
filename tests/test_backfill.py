from __future__ import annotations

from datetime import date

from extract.backfill import months, pending


def test_months_covers_both_ends():
    assert months(date(2024, 1, 5), date(2024, 3, 20)) == [
        date(2024, 1, 1), date(2024, 2, 1), date(2024, 3, 1)
    ]


def test_a_single_month_is_one_partition():
    assert months(date(2024, 6, 1), date(2024, 6, 30)) == [date(2024, 6, 1)]


def test_months_crosses_a_year():
    assert months(date(2023, 11, 2), date(2024, 2, 2)) == [
        date(2023, 11, 1), date(2023, 12, 1), date(2024, 1, 1), date(2024, 2, 1)
    ]


def test_a_reversed_range_asks_for_nothing():
    assert months(date(2024, 6, 1), date(2024, 1, 1)) == []


def test_partitions_already_held_are_not_fetched_again():
    wanted = [date(2024, 1, 1), date(2024, 2, 1), date(2024, 3, 1)]

    assert pending({date(2024, 1, 1)}, wanted, force=False) == [date(2024, 2, 1), date(2024, 3, 1)]


def test_force_fetches_everything_regardless():
    wanted = [date(2024, 1, 1), date(2024, 2, 1)]

    assert pending(set(wanted), wanted, force=True) == wanted
