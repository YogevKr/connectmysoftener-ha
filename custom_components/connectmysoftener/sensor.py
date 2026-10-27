"""Sensors for the ConnectMySoftener integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfTime,
    UnitOfVolume,
    UnitOfVolumeFlowRate,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import ConnectMySoftenerConfigEntry
from .const import DOMAIN
from .coordinator import ConnectMySoftenerCoordinator

_LOGGER = logging.getLogger(__name__)

FLOW_SCAN_INTERVAL = timedelta(seconds=30)


def _clean(value: Any) -> Any:
    """Return a whole number when the value has no fraction."""
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


@dataclass(frozen=True, kw_only=True)
class SoftenerSensorDescription(SensorEntityDescription):
    """Describe one softener sensor."""


SENSORS: tuple[SoftenerSensorDescription, ...] = (
    SoftenerSensorDescription(
        key="status",
        name="Status",
        icon="mdi:water-check",
    ),
    SoftenerSensorDescription(
        key="salt_level",
        name="Salt level",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:shaker-outline",
    ),
    SoftenerSensorDescription(
        key="remaining_water",
        name="Remaining water",
        native_unit_of_measurement=UnitOfVolume.LITERS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:water",
    ),
    SoftenerSensorDescription(
        key="days_remaining",
        name="Days until regeneration",
        native_unit_of_measurement=UnitOfTime.DAYS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:calendar",
    ),
    SoftenerSensorDescription(
        key="last_regeneration",
        name="Last regeneration",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:history",
    ),
    SoftenerSensorDescription(
        key="regenerations",
        name="Regenerations",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:counter",
    ),
    SoftenerSensorDescription(
        key="total_volume",
        name="Total treated water",
        native_unit_of_measurement=UnitOfVolume.LITERS,
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:chart-bar",
    ),
    SoftenerSensorDescription(
        key="daily_consumption",
        name="Daily consumption",
        native_unit_of_measurement=UnitOfVolume.LITERS,
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.TOTAL,
        icon="mdi:counter",
    ),
    SoftenerSensorDescription(
        key="flow",
        name="Water flow",
        native_unit_of_measurement=UnitOfVolumeFlowRate.LITERS_PER_MINUTE,
        device_class=SensorDeviceClass.VOLUME_FLOW_RATE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:water-pump",
    ),
    SoftenerSensorDescription(
        key="software_version",
        name="Software version",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:information-outline",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConnectMySoftenerConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add every sensor of one softener."""
    coordinator = entry.runtime_data
    async_add_entities(
        SoftenerFlowSensor(coordinator, description)
        if description.key == "flow"
        else SoftenerSensor(coordinator, description)
        for description in SENSORS
    )


class SoftenerSensor(CoordinatorEntity[ConnectMySoftenerCoordinator], SensorEntity):
    """One value of the softener."""

    entity_description: SoftenerSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ConnectMySoftenerCoordinator,
        description: SoftenerSensorDescription,
    ) -> None:
        """Set up the entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}_{coordinator.device_id}_{description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> Any:
        """Return the current value."""
        return _clean(self.coordinator.data.get(self.entity_description.key))

    @property
    def last_reset(self) -> datetime | None:
        """Reset the daily counter at local midnight."""
        if self.entity_description.state_class == SensorStateClass.TOTAL:
            return dt_util.start_of_local_day()
        return None


class SoftenerFlowSensor(SoftenerSensor):
    """Water flow, polled faster than the other values."""

    def __init__(
        self,
        coordinator: ConnectMySoftenerCoordinator,
        description: SoftenerSensorDescription,
    ) -> None:
        """Set up the entity."""
        super().__init__(coordinator, description)
        self._value: float | None = None

    @property
    def native_value(self) -> Any:
        """Return the last flow value."""
        if self._value is not None:
            return _clean(self._value)
        return super().native_value

    async def async_added_to_hass(self) -> None:
        """Start the fast poll."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_time_interval(self.hass, self._async_update_flow, FLOW_SCAN_INTERVAL)
        )

    async def _async_update_flow(self, now: datetime) -> None:
        """Read the flow and write it to the state machine."""
        value = await self.coordinator.async_get_flow()
        if value is None or value == self._value:
            return
        self._value = value
        self.async_write_ha_state()
