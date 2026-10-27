"""Tests for the sensor entities."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from custom_components.connectmysoftener.sensor import SENSORS, SoftenerFlowSensor


class FakeCoordinator:
    """Minimal stand-in for the data update coordinator."""

    device_id = 1234
    device_info = None

    def __init__(self, flow: float | None) -> None:
        self.data: dict[str, Any] = {"flow": flow}
        self._flow = flow
        self.flow_calls = 0

    async def async_get_flow(self) -> float | None:
        """Return the configured flow."""
        self.flow_calls += 1
        return self._flow


def build_flow_sensor(coordinator: FakeCoordinator) -> SoftenerFlowSensor:
    """Return a flow sensor that writes into a list."""
    description = next(item for item in SENSORS if item.key == "flow")
    return SoftenerFlowSensor(coordinator, description)  # type: ignore[arg-type]


def test_flow_sensor_writes_again_when_the_value_repeats() -> None:
    """A repeated reading must still be written, because flow is a live value."""
    coordinator = FakeCoordinator(0.0)
    entity = build_flow_sensor(coordinator)
    writes: list[int] = []
    entity.async_write_ha_state = lambda: writes.append(1)  # type: ignore[method-assign]

    asyncio.run(entity._async_update_flow(None))  # type: ignore[arg-type]
    asyncio.run(entity._async_update_flow(None))  # type: ignore[arg-type]

    assert coordinator.flow_calls == 2
    assert len(writes) == 2
    assert entity.native_value == 0


def test_flow_sensor_keeps_the_last_value() -> None:
    """The sensor reports the value of the fast poll."""
    coordinator = FakeCoordinator(7.5)
    entity = build_flow_sensor(coordinator)
    entity.async_write_ha_state = lambda: None  # type: ignore[method-assign]

    asyncio.run(entity._async_update_flow(None))  # type: ignore[arg-type]

    assert entity.native_value == 7.5


def test_flow_sensor_skips_a_failed_poll() -> None:
    """A failed poll keeps the old value."""
    coordinator = FakeCoordinator(3.0)
    entity = build_flow_sensor(coordinator)
    entity.async_write_ha_state = lambda: None  # type: ignore[method-assign]
    asyncio.run(entity._async_update_flow(None))  # type: ignore[arg-type]

    coordinator._flow = None
    asyncio.run(entity._async_update_flow(None))  # type: ignore[arg-type]

    assert entity.native_value == 3.0


@pytest.mark.parametrize("key", [item.key for item in SENSORS])
def test_every_sensor_has_a_name(key: str) -> None:
    """Every sensor needs a name and a unique id key."""
    description = next(item for item in SENSORS if item.key == key)

    assert description.name


class RaisingCoordinator(FakeCoordinator):
    """Coordinator whose flow call fails, as during a shutdown."""

    async def async_get_flow(self) -> float | None:
        """Raise like a closed aiohttp session."""
        raise RuntimeError("Session is closed")


def test_flow_sensor_survives_a_closed_session() -> None:
    """The timer task must not raise when Home Assistant shuts down."""
    entity = build_flow_sensor(RaisingCoordinator(1.0))
    entity.async_write_ha_state = lambda: None  # type: ignore[method-assign]

    asyncio.run(entity._async_update_flow(None))  # type: ignore[arg-type]

    assert entity.native_value == 1.0
