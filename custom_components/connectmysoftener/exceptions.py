"""Exceptions for the ConnectMySoftener integration."""

from __future__ import annotations


class ConnectMySoftenerError(Exception):
    """Base exception for this integration."""


class CannotConnect(ConnectMySoftenerError):
    """The cloud API did not answer."""


class InvalidAuth(ConnectMySoftenerError):
    """The account rejected the credentials."""


class NoDevicesFound(ConnectMySoftenerError):
    """The account holds no softener."""
