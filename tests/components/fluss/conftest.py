"""Shared test fixtures for Fluss+ integration."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.components.fluss.const import (
    CONF_SCAN_INTERVAL_STATUS,
    DEFAULT_SCAN_INTERVAL_STATUS_MINUTES,
    DOMAIN,
)
from homeassistant.const import CONF_API_KEY

from tests.common import MockConfigEntry


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return the default mocked config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="My Fluss+ Devices",
        data={
            CONF_API_KEY: "test_api_key",
            CONF_SCAN_INTERVAL_STATUS: DEFAULT_SCAN_INTERVAL_STATUS_MINUTES,
        },
    )


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Override async_setup_entry."""
    with patch(
        "homeassistant.components.fluss.async_setup_entry", return_value=True
    ) as mock_setup_entry:
        yield mock_setup_entry


@pytest.fixture
def mock_api_client() -> Generator[AsyncMock]:
    """Mock Fluss API client with a single device and a default status payload."""
    with (
        patch(
            "homeassistant.components.fluss.FlussApiClient",
            autospec=True,
        ) as mock_client,
        patch(
            "homeassistant.components.fluss.config_flow.FlussApiClient",
            new=mock_client,
        ),
    ):
        client = mock_client.return_value
        client.async_get_devices.return_value = {
            "devices": [
                {"deviceId": "2a303030sdj1", "deviceName": "Device 1"},
                {"deviceId": "ape93k9302j2", "deviceName": "Device 2"},
            ]
        }
        client.async_get_device_status.return_value = {
            "status": {
                "deviceId": "abc123",
                "internetConnected": True,
                "connectionTimeStamp": 1711324800000,
                "updatedTimeStamp": 1711324860000,
                "ipAddress": "192.168.1.50",
                "openCloseStatus": "Closed",
                "fwv": "2.1.4",
                "ssid": "HomeWifi",
                "rssi": -42,
            }
        }
        yield client
