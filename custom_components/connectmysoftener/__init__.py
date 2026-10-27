"""Set up the ConnectMySoftener integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ConnectMySoftenerApi
from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN
from .coordinator import ConnectMySoftenerCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)

type ConnectMySoftenerConfigEntry = ConfigEntry[ConnectMySoftenerCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: ConnectMySoftenerConfigEntry) -> bool:
    """Set up one softener from a config entry."""
    session = async_get_clientsession(hass)
    api = ConnectMySoftenerApi(
        session,
        email=entry.data["email"],
        password=entry.data["password"],
    )
    coordinator = ConnectMySoftenerCoordinator(
        hass,
        entry,
        api,
        device_id=entry.data["device_id"],
        scan_interval=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
    )
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConnectMySoftenerConfigEntry) -> bool:
    """Unload one softener."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    hass.data[DOMAIN].pop(entry.entry_id)
    return True
