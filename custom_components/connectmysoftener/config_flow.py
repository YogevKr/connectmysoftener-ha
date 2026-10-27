"""Config and options flow for the ConnectMySoftener integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlowWithReload
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ConnectMySoftenerApi
from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .exceptions import CannotConnect, InvalidAuth, NoDevicesFound

_LOGGER = logging.getLogger(__name__)

_USER_SCHEMA = vol.Schema(
    {
        vol.Required("email"): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.EMAIL)
        ),
        vol.Required("password"): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
        ),
    }
)


class ConnectMySoftenerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the setup of one account."""

    VERSION = 1

    def __init__(self) -> None:
        """Set up the flow."""
        self._devices: list[dict[str, Any]] = []
        self._email: str | None = None
        self._password: str | None = None

    async def _async_login(self, email: str, password: str) -> list[dict[str, Any]]:
        """Log in and return the softeners, or raise a flow error."""
        session = async_get_clientsession(self.hass)
        api = ConnectMySoftenerApi(session, email=email, password=password)
        await api.async_authenticate()
        devices = await api.async_get_devices()
        if not devices:
            raise NoDevicesFound
        return devices

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ask for the account of the app."""
        errors: dict[str, str] = {}
        if user_input is not None:
            email = user_input["email"]
            password = user_input["password"]
            try:
                devices = await self._async_login(email, password)
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except NoDevicesFound:
                errors["base"] = "no_devices"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during login")
                errors["base"] = "unknown"
            else:
                if len(devices) == 1:
                    return await self._async_create_entry(devices[0], email, password)
                self._devices = devices
                self._email = email
                self._password = password
                return await self.async_step_select_device()

        return self.async_show_form(step_id="user", data_schema=_USER_SCHEMA, errors=errors)

    async def async_step_select_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user pick one softener from several."""
        if user_input is not None:
            device = next(
                item for item in self._devices if str(item["id"]) == user_input["device_id"]
            )
            return await self._async_create_entry(device, self._email, self._password)

        options = {
            str(item["id"]): item["name"] + (f" ({item['serial']})" if item.get("serial") else "")
            for item in self._devices
        }
        return self.async_show_form(
            step_id="select_device",
            data_schema=vol.Schema({vol.Required("device_id"): vol.In(options)}),
        )

    async def _async_create_entry(
        self, device: dict[str, Any], email: str | None, password: str | None
    ) -> ConfigFlowResult:
        """Create the config entry for one softener."""
        await self.async_set_unique_id(str(device["id"]))
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=device["name"],
            data={"email": email, "password": password, "device_id": device["id"]},
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Start the reauth flow after a rejected password."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for a new password."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            email = user_input["email"]
            password = user_input["password"]
            try:
                await self._async_login(email, password)
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect, NoDevicesFound:
                errors["base"] = "cannot_connect"
            else:
                self.hass.config_entries.async_update_entry(
                    entry, data={**entry.data, "email": email, "password": password}
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=self.add_suggested_values_to_schema(_USER_SCHEMA, entry.data),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> ConnectMySoftenerOptionsFlow:
        """Return the options flow."""
        return ConnectMySoftenerOptionsFlow()


class ConnectMySoftenerOptionsFlow(OptionsFlowWithReload):
    """Change the poll interval."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Show the options form."""
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL])},
            )

        current = self.config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SCAN_INTERVAL, default=current): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=MIN_SCAN_INTERVAL,
                            max=MAX_SCAN_INTERVAL,
                            step=10,
                            unit_of_measurement="s",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    )
                }
            ),
        )
