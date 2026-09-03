"""The warehouse connection is described once, in the parts dbt reads."""

from __future__ import annotations

from extract.load import warehouse_url

PARTS = {
    "WAREHOUSE_USER": "u",
    "WAREHOUSE_PASSWORD": "p",
    "WAREHOUSE_HOST": "h",
    "WAREHOUSE_PORT": "5432",
    "WAREHOUSE_DB": "d",
    "WAREHOUSE_SSLMODE": "require",
}


def test_the_url_is_assembled_from_the_parts_dbt_also_reads(monkeypatch):
    monkeypatch.delenv("WAREHOUSE_URL", raising=False)
    for name, value in PARTS.items():
        monkeypatch.setenv(name, value)

    assert warehouse_url() == "postgresql://u:p@h:5432/d?sslmode=require"


def test_a_whole_url_overrides_the_parts(monkeypatch):
    monkeypatch.setenv("WAREHOUSE_URL", "postgresql://given/directly")
    monkeypatch.setenv("WAREHOUSE_HOST", "ignored")

    assert warehouse_url() == "postgresql://given/directly"


def test_the_local_default_needs_no_environment(monkeypatch):
    for name in ["WAREHOUSE_URL", *PARTS]:
        monkeypatch.delenv(name, raising=False)

    # docker compose brings up the warehouse on this port.
    assert warehouse_url() == "postgresql://energy:energy@localhost:5435/energy?sslmode=prefer"
