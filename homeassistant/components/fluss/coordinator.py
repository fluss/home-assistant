"""DataUpdateCoordinator for Fluss+ integration."""

from __future__ import annotations

from typing import Any

from fluss_api import (
    FlussApiClient,
    FlussApiClientAuthenticationError,
    FlussApiClientError,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import slugify

from .const import LOGGER, UPDATE_INTERVAL_TIMEDELTA

type FlussConfigEntry = ConfigEntry[FlussDataUpdateCoordinator]

VALID_OPEN_CLOSE_STATUSES = {"Open", "Closed"}


def device_has_cover_status(device_data: dict[str, Any]) -> bool:
    """Return True if the device status contains a valid openCloseStatus."""
    status = device_data.get("status") or {}
    return status.get("openCloseStatus") in VALID_OPEN_CLOSE_STATUSES


class FlussDataUpdateCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Manages fetching Fluss device data on a schedule."""

    config_entry: FlussConfigEntry

    def __init__(
        self, hass: HomeAssistant, config_entry: FlussConfigEntry, api_key: str
    ) -> None:
        """Initialize the coordinator."""
        self.api = FlussApiClient(api_key, session=async_get_clientsession(hass))
        self._button_only_device_ids: set[str] = set()
        super().__init__(
            hass,
            LOGGER,
            name=f"Fluss+ ({slugify(api_key[:8])})",
            config_entry=config_entry,
            update_interval=UPDATE_INTERVAL_TIMEDELTA,
        )

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        """Fetch data from the Fluss API and return as a dictionary keyed by deviceId."""
        try:
            devices = await self.api.async_get_devices()
        except FlussApiClientAuthenticationError as err:
            raise ConfigEntryError(f"Authentication failed: {err}") from err
        except FlussApiClientError as err:
            raise UpdateFailed(f"Error fetching Fluss devices: {err}") from err

        device_list = devices.get("devices", [])
        result: dict[str, dict[str, Any]] = {}
        for device in device_list:
            device_id = device["deviceId"]
            if device_id in self._button_only_device_ids:
                # Known non-cover device — skip status polling to avoid
                # hammering the API with requests that never yield cover state.
                result[device_id] = {**device, "status": {}}
                continue

            status = await self._async_get_device_status(device_id)
            if (
                status is not None
                and status.get("openCloseStatus") not in VALID_OPEN_CLOSE_STATUSES
            ):
                self._button_only_device_ids.add(device_id)
            result[device_id] = {**device, "status": status}

        return result

    async def _async_get_device_status(self, device_id: str) -> dict[str, Any] | None:
        """Fetch status for a single device, returning None on failure."""
        try:
            response = await self.api.async_get_device_status(device_id)
        except FlussApiClientError as err:
            LOGGER.debug("Failed to get status for device %s: %s", device_id, err)
            return None
        status = response.get("status") if isinstance(response, dict) else None
        return status if isinstance(status, dict) else None
