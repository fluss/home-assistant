"""Binary sensor platform for the Fluss+ integration."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FlussConfigEntry, FlussStatusCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FlussConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Fluss+ binary sensors."""
    runtime = entry.runtime_data
    async_add_entities(
        FlussInternetBinarySensor(runtime.status_coordinator, device_id, device)
        for device_id, device in runtime.list_coordinator.data.items()
    )


class FlussInternetBinarySensor(
    CoordinatorEntity[FlussStatusCoordinator], BinarySensorEntity
):
    """Reports whether a Fluss+ device currently has an internet connection."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_translation_key = "internet"

    def __init__(
        self,
        coordinator: FlussStatusCoordinator,
        device_id: str,
        device: dict,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}_internet"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device.get("deviceName"),
            manufacturer="Fluss",
            model="Fluss+ Device",
        )

    @property
    def available(self) -> bool:
        """Return if the device's status has been reported."""
        return super().available and self._device_id in self.coordinator.data

    @property
    def is_on(self) -> bool | None:
        """Return True if the device is connected to the internet."""
        status = self.coordinator.data.get(self._device_id)
        if status is None:
            return None
        return bool(status.get("internetConnected"))
