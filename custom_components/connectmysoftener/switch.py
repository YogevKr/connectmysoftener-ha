"""Holiday-mode switch for the ConnectMySoftener integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ConnectMySoftenerConfigEntry
from .const import DOMAIN, HOLIDAY_MODE_MAX_DAYS
from .coordinator import ConnectMySoftenerCoordinator

_LOGGER = logging.getLogger(__name__)


def holiday_is_on(value: Any) -> bool:
    """Read holiday state. The dashboard field is a bool on some firmwares, days on others."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value > 0
    return False


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConnectMySoftenerConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the holiday switch."""
    async_add_entities([SoftenerHolidaySwitch(entry.runtime_data)])


class SoftenerHolidaySwitch(CoordinatorEntity[ConnectMySoftenerCoordinator], SwitchEntity):
    """Turn the softener's holiday (vacation) mode on or off."""

    _attr_has_entity_name = True
    _attr_name = "Holiday mode"
    _attr_icon = "mdi:palm-tree"

    def __init__(self, coordinator: ConnectMySoftenerCoordinator) -> None:
        """Set up the switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{coordinator.device_id}_holiday_mode"
        self._attr_device_info = coordinator.device_info

    @property
    def is_on(self) -> bool:
        """Return True when holiday mode is active."""
        return holiday_is_on(self.coordinator.data.get("holiday_mode"))

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Start holiday mode for the longest allowed span."""
        await self.coordinator.api.async_set_holiday_mode(
            self.coordinator.device_id, HOLIDAY_MODE_MAX_DAYS
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Stop holiday mode."""
        await self.coordinator.api.async_set_holiday_mode(self.coordinator.device_id, 0)
        await self.coordinator.async_request_refresh()
