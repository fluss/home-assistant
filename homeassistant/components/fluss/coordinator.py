"""DataUpdateCoordinators for the Fluss+ integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from fluss_api import (
    FlussApiClient,
    FlussApiClientAuthenticationError,
    FlussApiClientError,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import slugify

from .const import (
    CONF_SCAN_INTERVAL_STATUS,
    DEFAULT_SCAN_INTERVAL_STATUS_MINUTES,
    DEVICE_LIST_UPDATE_INTERVAL,
    LOGGER,
)


@dataclass
class FlussData:
    """Runtime data held on the config entry."""

    list_coordinator: FlussDataUpdateCoordinator
    status_coordinator: FlussStatusCoordinator


type FlussConfigEntry = ConfigEntry[FlussData]


class FlussDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Manages fetching the Fluss+ device list on a fixed schedule."""

    def __init__(
        self, hass: HomeAssistant, config_entry: FlussConfigEntry, api: FlussApiClient
    ) -> None:
        """Initialize the coordinator."""
        self.api = api
        super().__init__(
            hass,
            LOGGER,
            name=f"Fluss+ ({slugify(config_entry.entry_id[:8])})",
            config_entry=config_entry,
            update_interval=DEVICE_LIST_UPDATE_INTERVAL,
        )

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        """Fetch the device list from the Fluss API."""
        try:
            devices = await self.api.async_get_devices()
        except FlussApiClientAuthenticationError as err:
            raise ConfigEntryError(f"Authentication failed: {err}") from err
        except FlussApiClientError as err:
            raise UpdateFailed(f"Error fetching Fluss devices: {err}") from err

        return {device["deviceId"]: device for device in devices.get("devices", [])}


class FlussStatusCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Polls the per-device status endpoint at a user-configured interval."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: FlussConfigEntry,
        list_coordinator: FlussDataUpdateCoordinator,
    ) -> None:
        """Initialize the status coordinator."""
        self.api = list_coordinator.api
        self._list_coordinator = list_coordinator
        interval_minutes = config_entry.data.get(
            CONF_SCAN_INTERVAL_STATUS, DEFAULT_SCAN_INTERVAL_STATUS_MINUTES
        )
        super().__init__(
            hass,
            LOGGER,
            name=f"Fluss+ status ({slugify(config_entry.entry_id[:8])})",
            config_entry=config_entry,
            update_interval=timedelta(minutes=interval_minutes),
        )

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        """Fetch the current status for each known device."""
        statuses: dict[str, dict[str, Any]] = {}
        for device_id in self._list_coordinator.data or {}:
            try:
                result = await self.api.async_get_device_status(device_id)
            except FlussApiClientAuthenticationError as err:
                raise ConfigEntryError(f"Authentication failed: {err}") from err
            except FlussApiClientError as err:
                raise UpdateFailed(
                    f"Error fetching Fluss status: {err}"
                ) from err
            if isinstance(result, dict):
                status = result.get("status")
                if isinstance(status, dict):
                    statuses[device_id] = status
        return statuses
