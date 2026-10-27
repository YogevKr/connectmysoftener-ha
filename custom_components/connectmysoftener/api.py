"""Client for the Pentair / Erie ConnectMySoftener cloud API.

The API is a Rails backend that authenticates with devise-token-auth. A login
returns four headers that must be sent with every later request. The backend
can rotate ``Access-Token`` on any answer, so fresh headers from every response
replace the stored ones.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, date, datetime
from typing import Any

import aiohttp

from .exceptions import CannotConnect, InvalidAuth

_LOGGER = logging.getLogger(__name__)

API_BASE_URL = "https://connectmysoftenerapi.pentair.eu/api/erieapp/v1"
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=30)

AUTH_HEADERS = ("Access-Token", "Client", "Uid", "Token-Type")

_DATETIME_FORMATS = (
    "%Y-%m-%dT%H:%M:%S.%f%z",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y",
)


def parse_datetime(value: Any) -> datetime | None:
    """Return a timezone-aware datetime, or None when the text has no known shape."""
    if not value or not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    candidate = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        parsed = None
    if parsed is None:
        for shape in _DATETIME_FORMATS:
            try:
                parsed = datetime.strptime(text, shape)
            except ValueError:
                continue
            break
    if parsed is None:
        _LOGGER.warning("Cannot read date value %r from the API", text)
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def parse_number(value: Any, default: float | None = None) -> float | None:
    """Return the leading number of a value such as ``"3392 L"``."""
    if value is None or isinstance(value, bool):
        return default
    if isinstance(value, int | float):
        return float(value)
    text = str(value).strip()
    if not text:
        return default
    try:
        return float(text.split()[0])
    except ValueError, IndexError:
        _LOGGER.debug("Cannot read number value %r from the API", text)
        return default


def parse_data(raw: dict[str, Any]) -> dict[str, Any]:
    """Turn the raw API answers into flat sensor values."""
    dashboard = raw.get("dashboard") or {}
    status = dashboard.get("status") or {}
    info = raw.get("info") or {}
    flow = raw.get("flow") or {}
    graph = raw.get("graph") or {}

    if isinstance(graph, dict):
        graph_points = graph.get("graph") or []
    elif isinstance(graph, list):
        graph_points = graph
    else:
        graph_points = []

    daily_consumption = 0.0
    for point in graph_points:
        if isinstance(point, dict):
            daily_consumption += parse_number(point.get("y"), 0.0) or 0.0

    software = info.get("software")
    serial = info.get("serial")

    return {
        "status": status.get("title"),
        "salt_level": parse_number(status.get("percentage")),
        "remaining_water": parse_number(status.get("extra")),
        "days_remaining": parse_number(status.get("days_remaining")),
        "last_regeneration": parse_datetime(info.get("last_regeneration")),
        "regenerations": parse_number(info.get("nr_regenerations"), 0.0),
        "total_volume": parse_number(info.get("total_volume"), 0.0),
        "daily_consumption": daily_consumption,
        "flow": parse_number(flow.get("flow"), 0.0),
        "software_version": software.strip()
        if isinstance(software, str) and software.strip()
        else None,
        "serial_number": serial if isinstance(serial, str) and serial else None,
    }


class ConnectMySoftenerApi:
    """Thin async client for the ConnectMySoftener cloud API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        email: str,
        password: str,
        base_url: str = API_BASE_URL,
    ) -> None:
        """Set up the client."""
        self._session = session
        self._email = email
        self._password = password
        self._base_url = base_url
        self._auth_headers: dict[str, str] = {}
        self._auth_lock = asyncio.Lock()

    @property
    def auth_headers(self) -> dict[str, str]:
        """Return a copy of the current auth headers."""
        return dict(self._auth_headers)

    async def async_authenticate(self) -> None:
        """Log in and store the auth headers. Raises InvalidAuth or CannotConnect."""
        payload = {"email": self._email, "password": self._password}
        try:
            response = await self._session.post(
                f"{self._base_url}/auth/sign_in",
                json=payload,
                timeout=REQUEST_TIMEOUT,
            )
        except (aiohttp.ClientError, TimeoutError, RuntimeError) as err:
            raise CannotConnect(f"Login failed: {err}") from err

        async with response:
            if response.status in (401, 403):
                raise InvalidAuth("The account rejected the email or the password")
            if response.status >= 400:
                raise CannotConnect(f"Login returned HTTP {response.status}")
            self._store_auth_headers(response.headers)

        if not all(self._auth_headers.get(key) for key in AUTH_HEADERS):
            raise CannotConnect("Login answered without auth headers")

    def _store_auth_headers(self, headers: aiohttp.typedefs.LooseHeaders) -> None:
        """Copy every auth header that the answer carries."""
        for key in AUTH_HEADERS:
            value = headers.get(key) if headers is not None else None
            if value:
                self._auth_headers[key] = str(value).strip()

    async def _async_request(self, path: str, *, retry_on_auth_error: bool = True) -> Any:
        """Run one authenticated GET request."""
        if not self._auth_headers:
            async with self._auth_lock:
                if not self._auth_headers:
                    await self.async_authenticate()

        try:
            response = await self._session.get(
                f"{self._base_url}/{path}",
                headers=self._auth_headers,
                timeout=REQUEST_TIMEOUT,
            )
        except (aiohttp.ClientError, TimeoutError, RuntimeError) as err:
            raise CannotConnect(f"GET {path} failed: {err}") from err

        async with response:
            if response.status == 401 and retry_on_auth_error:
                _LOGGER.debug("Session expired, logging in again")
                async with self._auth_lock:
                    await self.async_authenticate()
                return await self._async_request(path, retry_on_auth_error=False)

            self._store_auth_headers(response.headers)

            if response.status >= 400:
                raise CannotConnect(f"GET {path} returned HTTP {response.status}")

            try:
                return await response.json(content_type=None)
            except (aiohttp.ClientError, ValueError) as err:
                raise CannotConnect(f"GET {path} returned no JSON: {err}") from err

    async def async_get_devices(self) -> list[dict[str, Any]]:
        """Return every softener of the account."""
        data = await self._async_request("water_softeners")
        if not isinstance(data, list):
            return []
        devices = []
        for item in data:
            profile = item.get("profile") if isinstance(item, dict) else None
            if not isinstance(profile, dict) or profile.get("id") is None:
                continue
            devices.append(
                {
                    "id": profile["id"],
                    "name": profile.get("name") or f"Softener {profile['id']}",
                    "serial": profile.get("serial"),
                }
            )
        return devices

    async def async_get_data(self, device_id: int | str) -> dict[str, Any]:
        """Fetch every sensor endpoint for one softener."""
        today = date.today()
        paths = {
            "dashboard": f"water_softeners/{device_id}/dashboard",
            "info": f"water_softeners/{device_id}/info",
            "flow": f"water_softeners/{device_id}/flow",
            "graph": (
                f"water_softeners/{device_id}/graphs/day"
                f"?day={today.day}&month={today.month}&year={today.year}"
            ),
        }

        results = await asyncio.gather(
            *(self._async_request(path) for path in paths.values()),
            return_exceptions=True,
        )

        raw: dict[str, Any] = {}
        errors: list[Exception] = []
        for name, result in zip(paths, results, strict=True):
            if isinstance(result, Exception):
                errors.append(result)
            else:
                raw[name] = result

        if len(errors) == len(paths):
            raise CannotConnect(f"Every endpoint failed: {errors[0]}")

        if errors:
            _LOGGER.debug("Some endpoints failed, using the rest: %s", errors)

        return parse_data(raw)

    async def async_get_flow(self, device_id: int | str) -> float | None:
        """Fetch only the current water flow."""
        data = await self._async_request(f"water_softeners/{device_id}/flow")
        if not isinstance(data, dict):
            return None
        return parse_number(data.get("flow"))
