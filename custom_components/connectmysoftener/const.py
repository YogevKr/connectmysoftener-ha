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
