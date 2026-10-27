"""Data update coordinator for the ConnectMySoftener integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ConnectMySoftenerApi
from .const import DEVICE_NAME, DOMAIN, MANUFACTURER, MODEL
from .exceptions import CannotConnect, InvalidAuth

_LOGGER = logging.getLogger(__name__)


class ConnectMySoftenerCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Poll one softener and keep the shared device info."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api: ConnectMySoftenerApi,
        device_id: int | str,
        scan_interval: int,
    ) -> None:
        """Set up the coordinator."""
        self.api = api
        self.device_id = device_id
        self.device_info: DeviceInfo | None = None
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {device_id}",
            update_interval=timedelta(seconds=scan_interval),
            config_entry=entry,
        )

    def set_scan_interval(self, scan_interval: int) -> None:
        """Apply a new poll interval."""
        self.update_interval = timedelta(seconds=scan_interval)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch the values of every sensor."""
        try:
            data = await self.api.async_get_data(self.device_id)
        except InvalidAuth as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except CannotConnect as err:
            raise UpdateFailed(str(err)) from err

        if not data:
            raise UpdateFailed("The API answered without values")

        self._update_device_info(data)
        return data

    def _update_device_info(self, data: dict[str, Any]) -> None:
        """Build the device entry once the serial number is known."""
        serial = data.get("serial_number") or str(self.device_id)
        if self.device_info is not None and self.device_info.get("serial_number") == serial:
            software = data.get("software_version")
            if software:
                self.device_info["sw_version"] = software
            return
        self.device_info = DeviceInfo(
            identifiers={(DOMAIN, serial)},
            name=DEVICE_NAME,
            manufacturer=MANUFACTURER,
            model=MODEL,
            serial_number=serial,
            sw_version=data.get("software_version"),
            configuration_url="https://connectmysoftenerapi.pentair.eu",
        )

    async def async_get_flow(self) -> float | None:
        """Fetch the current water flow without touching the other values."""
        try:
            return await self.api.async_get_flow(self.device_id)
        except (CannotConnect, InvalidAuth) as err:
            _LOGGER.debug("Flow update failed: %s", err)
            return None
