"""Action buttons for the ConnectMySoftener integration."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ConnectMySoftenerConfigEntry
from .api import ConnectMySoftenerApi
from .const import DOMAIN, REGEN_AT_SCHEDULED, REGEN_NOW
from .coordinator import ConnectMySoftenerCoordinator


@dataclass(frozen=True, kw_only=True)
class SoftenerButtonDescription(ButtonEntityDescription):
    """Describe one softener action button."""

    press_fn: Callable[[ConnectMySoftenerApi, int | str], Coroutine[Any, Any, Any]]


BUTTONS: tuple[SoftenerButtonDescription, ...] = (
    SoftenerButtonDescription(
        key="regenerate_now",
        name="Regenerate now",
        icon="mdi:refresh",
        press_fn=lambda api, device_id: api.async_regenerate(device_id, REGEN_NOW),
    ),
    SoftenerButtonDescription(
        key="regenerate_scheduled",
        name="Regenerate at scheduled time",
        icon="mdi:clock-outline",
        press_fn=lambda api, device_id: api.async_regenerate(device_id, REGEN_AT_SCHEDULED),
    ),
    SoftenerButtonDescription(
        key="salt_added",
        name="Salt added",
        icon="mdi:shaker",
        press_fn=lambda api, device_id: api.async_set_salt_added(device_id),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConnectMySoftenerConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the action buttons."""
    coordinator = entry.runtime_data
    async_add_entities(SoftenerButton(coordinator, description) for description in BUTTONS)


class SoftenerButton(CoordinatorEntity[ConnectMySoftenerCoordinator], ButtonEntity):
    """One softener action (regenerate / salt added)."""

    entity_description: SoftenerButtonDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ConnectMySoftenerCoordinator,
        description: SoftenerButtonDescription,
    ) -> None:
        """Set up the button."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}_{coordinator.device_id}_{description.key}"
        self._attr_device_info = coordinator.device_info

    async def async_press(self) -> None:
        """Run the action, then refresh so the state reflects it."""
        await self.entity_description.press_fn(self.coordinator.api, self.coordinator.device_id)
        await self.coordinator.async_request_refresh()
