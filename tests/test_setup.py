"""Check that every module of the integration imports without a Home Assistant instance."""

from __future__ import annotations

import importlib


def test_modules_import() -> None:
    """Every module must import cleanly."""
    for name in (
        "custom_components.connectmysoftener",
        "custom_components.connectmysoftener.api",
        "custom_components.connectmysoftener.button",
        "custom_components.connectmysoftener.config_flow",
        "custom_components.connectmysoftener.const",
        "custom_components.connectmysoftener.coordinator",
        "custom_components.connectmysoftener.exceptions",
        "custom_components.connectmysoftener.number",
        "custom_components.connectmysoftener.sensor",
        "custom_components.connectmysoftener.switch",
    ):
        assert importlib.import_module(name) is not None


def test_sensors_have_unique_keys() -> None:
    """No sensor key may repeat."""
    from custom_components.connectmysoftener.sensor import SENSORS

    keys = [description.key for description in SENSORS]

    assert len(keys) == len(set(keys))
    assert "flow" in keys


def test_every_platform_is_set_up() -> None:
    """A platform that is not in the list gives entities that stay unavailable."""
    from homeassistant.const import Platform

    from custom_components.connectmysoftener import PLATFORMS

    assert set(PLATFORMS) == {
        Platform.SENSOR,
        Platform.SWITCH,
        Platform.NUMBER,
        Platform.BUTTON,
    }


def test_buttons_have_unique_keys() -> None:
    """No button key may repeat."""
    from custom_components.connectmysoftener.button import BUTTONS

    keys = [description.key for description in BUTTONS]

    assert len(keys) == len(set(keys))
