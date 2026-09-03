from __future__ import annotations

from datetime import date

import pytest

from extract.config import MAX_SPAN_DAYS, SERIES, Series
from extract.xm import SourceError, fetch_month, month_bounds, parse

SAMPLE = Series("PrecBolsNaci", "Sistema", date(2016, 1, 1), "spot price")


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError("not json")
        return self._payload


class FakeSession:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls: list[dict] = []

    def post(self, url, json, timeout):
        self.calls.append(json)
        return self.responses.pop(0)


def payload(*days):
    return {
        "Metric": {"Id": "PrecBolsNaci"},
        "Items": [
            {"Date": f"{day}T00:00:00", "HourlyEntities": [{"Values": {"code": "Sistema", "Hour01": "10.5", "Hour02": ""}}]}
            for day in days
        ],
    }


def test_a_month_never_exceeds_the_span_the_api_accepts():
    for month in (date(2024, 1, 9), date(2024, 2, 3), date(2024, 7, 31), date(2023, 2, 14)):
        first, last = month_bounds(month)
        assert first.day == 1
        assert (last - first).days <= MAX_SPAN_DAYS


def test_month_bounds_lands_on_the_last_day():
    assert month_bounds(date(2024, 2, 10)) == (date(2024, 2, 1), date(2024, 2, 29))
    assert month_bounds(date(2023, 2, 10)) == (date(2023, 2, 1), date(2023, 2, 28))
    assert month_bounds(date(2024, 12, 31)) == (date(2024, 12, 1), date(2024, 12, 31))


def test_parse_reads_one_record_per_entity_and_day():
    records = parse(payload("2024-01-01", "2024-01-02"), SAMPLE)

    assert [r.tx_date for r in records] == [date(2024, 1, 1), date(2024, 1, 2)]
    assert {r.resource_code for r in records} == {"Sistema"}
    # The code is the entity's identity, not one of its hours.
    assert "code" not in records[0].values
    assert records[0].values["Hour01"] == "10.5"


def test_parse_rejects_a_response_without_items():
    with pytest.raises(SourceError, match="no Items"):
        parse({"Message": "Id de Métrica no encontrada."}, SAMPLE)


def test_fetch_sends_the_whole_month_as_one_request():
    session = FakeSession(FakeResponse(payload=payload("2024-03-01")))

    fetch_month(SAMPLE, date(2024, 3, 15), session=session)

    assert session.calls == [
        {"MetricId": "PrecBolsNaci", "StartDate": "2024-03-01", "EndDate": "2024-03-31",
         "Entity": "Sistema"}
    ]


def test_a_two_hundred_that_is_not_json_is_an_error_not_a_result():
    # The API reports some failures as plain text with a 200.
    session = FakeSession(FakeResponse(text="Id de Métrica no encontrada."))

    with pytest.raises(SourceError, match="Métrica"):
        fetch_month(SAMPLE, date(2024, 3, 1), session=session)


def test_a_server_error_is_retried(monkeypatch):
    monkeypatch.setattr("extract.xm.time.sleep", lambda _: None)
    session = FakeSession(
        FakeResponse(status_code=503), FakeResponse(status_code=502),
        FakeResponse(payload=payload("2024-03-01")),
    )

    records = fetch_month(SAMPLE, date(2024, 3, 1), session=session)

    assert len(records) == 1
    assert len(session.calls) == 3


def test_a_client_error_is_not_retried():
    session = FakeSession(FakeResponse(status_code=400))

    with pytest.raises(SourceError, match="HTTP 400"):
        fetch_month(SAMPLE, date(2024, 3, 1), session=session)

    assert len(session.calls) == 1


def test_every_configured_series_has_its_own_key():
    keys = [series.key for series in SERIES]

    assert len(keys) == len(set(keys))
