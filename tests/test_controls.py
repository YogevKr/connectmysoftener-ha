"""Tests for the write calls and the control helpers."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from custom_components.connectmysoftener.api import ConnectMySoftenerApi, parse_data
from custom_components.connectmysoftener.const import (
    HOLIDAY_MODE_MAX_DAYS,
    REGEN_AT_SCHEDULED,
    REGEN_NOW,
)
from custom_components.connectmysoftener.switch import holiday_is_on


class RecordingApi(ConnectMySoftenerApi):
    """An API client that records each request and sends nothing."""

    def __init__(self) -> None:
        """Skip the session setup. The write helpers need only the request method."""
        self.calls: list[tuple[str, str, Any]] = []

    async def _async_request(
        self,
        path: str,
        *,
        method: str = "GET",
        json: Any = None,
        retry_on_auth_error: bool = True,
    ) -> Any:
        """Record the request."""
        self.calls.append((method, path, json))
        return None


@pytest.mark.parametrize(
    ("days", "expected"),
    [
        (0, 0),
        (1, 1),
        (HOLIDAY_MODE_MAX_DAYS, HOLIDAY_MODE_MAX_DAYS),
        (99, HOLIDAY_MODE_MAX_DAYS),
        (-3, 0),
    ],
)
def test_set_holiday_mode_writes_a_clamped_day_count(days: int, expected: int) -> None:
    """The day count stays between 0 and the maximum, and goes to the stats endpoint."""
    api = RecordingApi()

    asyncio.run(api.async_set_holiday_mode(7, days))

    assert api.calls == [("PUT", "water_softeners/7/stats", {"holiday_mode": expected})]


def test_salt_added_writes_the_flag() -> None:
    """The salt refill is one flag on the stats endpoint."""
    api = RecordingApi()

    asyncio.run(api.async_set_salt_added(7))

    assert api.calls == [("PUT", "water_softeners/7/stats", {"salt_added": True})]


@pytest.mark.parametrize("regen_type", [REGEN_NOW, REGEN_AT_SCHEDULED])
def test_regenerate_writes_the_action_code(regen_type: int) -> None:
    """Each regeneration type sends its own code."""
    api = RecordingApi()

    asyncio.run(api.async_regenerate(7, regen_type))

    assert api.calls == [("PUT", "water_softeners/7/stats", {"regenerate": regen_type})]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (True, True),
        (False, False),
        (0, False),
        (HOLIDAY_MODE_MAX_DAYS, True),
        (None, False),
        ("on", False),
    ],
)
def test_holiday_is_on(value: Any, expected: bool) -> None:
    """The holiday field is a bool on some firmwares and a day count on others."""
    assert holiday_is_on(value) is expected


def test_parse_data_reads_the_holiday_fields() -> None:
    """The holiday state and the status code come from the dashboard answer."""
    result = parse_data({"dashboard": {"holiday_mode": 40, "status": {"code": 3}}})

    assert result["holiday_mode"] == 40
    assert result["status_code"] == 3


def test_parse_data_without_holiday_fields() -> None:
    """A dashboard without the holiday field gives None, not an error."""
    result = parse_data({"dashboard": {"status": {}}})

    assert result["holiday_mode"] is None
    assert result["status_code"] is None
