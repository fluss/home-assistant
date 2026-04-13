"""The Fluss+ integration."""

from __future__ import annotations

from fluss_api import FlussApiClient

from homeassistant.const import CONF_API_KEY, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .coordinator import (
    FlussConfigEntry,
    FlussData,
    FlussDataUpdateCoordinator,
    FlussStatusCoordinator,
)

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.BUTTON]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FlussConfigEntry,
) -> bool:
    """Set up Fluss+ from a config entry."""
    api = FlussApiClient(
        entry.data[CONF_API_KEY], session=async_get_clientsession(hass)
    )
    list_coordinator = FlussDataUpdateCoordinator(hass, entry, api)
    await list_coordinator.async_config_entry_first_refresh()

    status_coordinator = FlussStatusCoordinator(hass, entry, list_coordinator)
    await status_coordinator.async_config_entry_first_refresh()

    entry.runtime_data = FlussData(
        list_coordinator=list_coordinator,
        status_coordinator=status_coordinator,
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: FlussConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
