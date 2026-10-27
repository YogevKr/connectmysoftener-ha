"""Tests for the ConnectMySoftener API helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from custom_components.connectmysoftener.api import parse_data, parse_datetime, parse_number


def build_payload(
    *,
    percentage: Any = 99,
    extra: Any = "3392 L",
    days_remaining: Any = 14,
    info: dict[str, Any] | None = None,
    flow: Any = 0,
    graph: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return an API answer that looks like the real one."""
    if info is None:
        info = {
            "last_regeneration": "",
            "nr_regenerations": 0,
            "total_volume": "0 L",
            "serial": "A0944260325",
            "software": " 74360 A02 D02",
        }
    if graph is None:
        graph = [{"name": "00", "y": 0}] * 24
    return {
        "dashboard": {
            "status": {
                "title": "In Service",
                "extra": extra,
                "percentage": percentage,
                "days_remaining": days_remaining,
            }
        },
        "info": info,
        "flow": {"flow": flow},
        "graph": {"graph": graph},
    }


def test_parse_data_reads_every_value() -> None:
    """Every sensor gets the value of the matching field."""
    result = parse_data(build_payload())

    assert result["status"] == "In Service"
    assert result["salt_level"] == 99.0
    assert result["remaining_water"] == 3392.0
    assert result["days_remaining"] == 14.0
    assert result["regenerations"] == 0.0
    assert result["total_volume"] == 0.0
    assert result["daily_consumption"] == 0.0
    assert result["flow"] == 0.0
    assert result["software_version"] == "74360 A02 D02"
    assert result["serial_number"] == "A0944260325"
    assert result["last_regeneration"] is None


def test_parse_data_always_reports_total_volume() -> None:
    """A zero total volume is a real value, not a missing key."""
    result = parse_data(build_payload(info={"total_volume": "0 L"}))

    assert result["total_volume"] == 0.0
    assert "total_volume" in result


def test_parse_data_sums_the_graph() -> None:
    """The daily consumption adds every hour of the graph."""
    graph = [{"name": f"{hour:02d}", "y": value} for hour, value in enumerate([0, 5, 10, 2])]
    graph += [{"name": "04", "y": 0}] * 20

    assert parse_data(build_payload(graph=graph))["daily_consumption"] == 17.0


def test_parse_data_accepts_a_graph_list() -> None:
    """The graph answer can be a bare list."""
    payload = build_payload()
    payload["graph"] = [{"name": "00", "y": 7}]

    assert parse_data(payload)["daily_consumption"] == 7.0


def test_parse_data_reads_an_iso_regeneration_date() -> None:
    """An ISO date becomes an aware datetime."""
    result = parse_data(build_payload(info={"last_regeneration": "2026-10-27T09:11:31.575Z"}))

    assert result["last_regeneration"] == datetime(2026, 10, 27, 9, 11, 31, 575000, tzinfo=UTC)


def test_parse_data_reads_a_regeneration_date_with_an_offset() -> None:
    """The date shape of the live API is accepted."""
    result = parse_data(build_payload(info={"last_regeneration": "2025-02-02T23:02:16+00:00"}))

    assert result["last_regeneration"] == datetime(2025, 2, 2, 23, 2, 16, tzinfo=UTC)


@pytest.mark.parametrize(
    ("payload", "key"),
    [
        ({"dashboard": {}, "info": {}, "flow": {}, "graph": {}}, "salt_level"),
        ({}, "remaining_water"),
        ({"dashboard": {"status": {"percentage": None}}}, "salt_level"),
        ({"dashboard": {"status": {"extra": ""}}}, "remaining_water"),
        ({"dashboard": {"status": {"extra": "nonsense"}}}, "remaining_water"),
        ({"graph": {"graph": "bad"}}, "daily_consumption"),
    ],
)
def test_parse_data_never_raises(payload: dict[str, Any], key: str) -> None:
    """A broken or empty answer still gives a usable dict."""
    result = parse_data(payload)

    assert key in result


def test_parse_number_reads_the_leading_number() -> None:
    """A value with a unit keeps only its number."""
    assert parse_number("3392 L") == 3392.0
    assert parse_number(14) == 14.0
    assert parse_number("", 0.0) == 0.0
    assert parse_number(None, 0.0) == 0.0
    assert parse_number(True, 9.0) == 9.0
    assert parse_number("abc", 1.0) == 1.0


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("", None),
        (None, None),
        ("2026-10-27T09:11:31Z", datetime(2026, 10, 27, 9, 11, 31, tzinfo=UTC)),
        ("2026-10-27 09:11:31", datetime(2026, 10, 27, 9, 11, 31, tzinfo=UTC)),
        # The shape that the real API uses when a regeneration happened.
        ("2025-02-02T23:02:16+00:00", datetime(2025, 2, 2, 23, 2, 16, tzinfo=UTC)),
        ("27/10/2026 09:11", datetime(2026, 10, 27, 9, 11, tzinfo=UTC)),
        ("nonsense", None),
    ],
)
def test_parse_datetime(value: Any, expected: datetime | None) -> None:
    """Only known shapes become a datetime."""
    assert parse_datetime(value) == expected
