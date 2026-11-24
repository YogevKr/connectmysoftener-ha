"""Holiday-days number for the ConnectMySoftener integration."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ConnectMySoftenerConfigEntry
from .const import DOMAIN, HOLIDAY_MODE_MAX_DAYS
from .coordinator import ConnectMySoftenerCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConnectMySoftenerConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the holiday-days number."""
    async_add_entities([SoftenerHolidayDays(entry.runtime_data)])


class SoftenerHolidayDays(CoordinatorEntity[ConnectMySoftenerCoordinator], NumberEntity):
    """Set holiday (vacation) mode for a chosen number of days. 0 = off."""

    _attr_has_entity_name = True
    _attr_name = "Holiday days"
    _attr_icon = "mdi:calendar-clock"
    _attr_native_min_value = 0
    _attr_native_max_value = HOLIDAY_MODE_MAX_DAYS
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX
    _attr_native_unit_of_measurement = UnitOfTime.DAYS
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: ConnectMySoftenerCoordinator) -> None:
        """Set up the number."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{coordinator.device_id}_holiday_days"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> float | None:
        """Return the remaining holiday days (0 when off)."""
        value = self.coordinator.data.get("holiday_mode")
        if isinstance(value, bool):
            return float(HOLIDAY_MODE_MAX_DAYS) if value else 0.0
        if isinstance(value, (int, float)):
            return float(value)
        return None

    async def async_set_native_value(self, value: float) -> None:
        """Write the holiday day count."""
        await self.coordinator.api.async_set_holiday_mode(self.coordinator.device_id, int(value))
        await self.coordinator.async_request_refresh()
