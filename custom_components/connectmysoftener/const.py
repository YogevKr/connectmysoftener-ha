"""Constants for the ConnectMySoftener integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "connectmysoftener"

CONF_SCAN_INTERVAL: Final = "scan_interval"

DEFAULT_SCAN_INTERVAL: Final = 300
MIN_SCAN_INTERVAL: Final = 30
MAX_SCAN_INTERVAL: Final = 3600

MANUFACTURER: Final = "Pentair / Erie"
MODEL: Final = "ConnectMySoftener"
DEVICE_NAME: Final = "Softener"

# Cloud API client headers. The backend rejects old app versions with HTTP 426.
APP_VERSION: Final = "9.9.9"
DEFAULT_LANGUAGE: Final = "en"

# Action codes written to PUT /water_softeners/{id}/stats.
REGEN_NOW: Final = 1
REGEN_AT_SCHEDULED: Final = 2
HOLIDAY_MODE_MAX_DAYS: Final = 40
