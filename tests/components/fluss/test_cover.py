"""Tests for the Fluss cover platform."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock

from fluss_api import FlussApiClientError
import pytest
from syrupy.assertion import SnapshotAssertion

from homeassistant.components.cover import (
    DOMAIN as COVER_DOMAIN,
    SERVICE_CLOSE_COVER,
    SERVICE_OPEN_COVER,
)
from homeassistant.components.fluss.cover import STATUS_REFRESH_DELAY
from homeassistant.const import ATTR_ENTITY_ID, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from . import setup_integration

from tests.common import MockConfigEntry, async_fire_time_changed, snapshot_platform


async def test_covers(
    hass: HomeAssistant,
    mock_api_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test cover entities are created for devices with openCloseStatus."""
    await setup_integration(hass, mock_config_entry)

    await snapshot_platform(hass, entity_registry, snapshot, mock_config_entry.entry_id)


async def test_cover_open(
    hass: HomeAssistant,
    mock_api_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test opening a cover."""
    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        COVER_DOMAIN,
        SERVICE_OPEN_COVER,
        {ATTR_ENTITY_ID: "cover.device_1"},
        blocking=True,
    )

    mock_api_client.async_open_device.assert_called_once_with("2a303030sdj1")


async def test_cover_close(
    hass: HomeAssistant,
    mock_api_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test closing a cover."""
    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        COVER_DOMAIN,
        SERVICE_CLOSE_COVER,
        {ATTR_ENTITY_ID: "cover.device_1"},
        blocking=True,
    )

    mock_api_client.async_close_device.assert_called_once_with("2a303030sdj1")


async def test_cover_open_error(
    hass: HomeAssistant,
    mock_api_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test cover open raises a translated HomeAssistantError on API failure."""
    await setup_integration(hass, mock_config_entry)

    mock_api_client.async_open_device.side_effect = FlussApiClientError("API Boom")

    with pytest.raises(HomeAssistantError) as exc_info:
        await hass.services.async_call(
            COVER_DOMAIN,
            SERVICE_OPEN_COVER,
            {ATTR_ENTITY_ID: "cover.device_1"},
            blocking=True,
        )

    assert exc_info.value.translation_domain == "fluss"
    assert exc_info.value.translation_key == "open_failed"
    assert exc_info.value.translation_placeholders == {"error": "API Boom"}


async def test_cover_close_error(
    hass: HomeAssistant,
    mock_api_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test cover close raises a translated HomeAssistantError on API failure."""
    await setup_integration(hass, mock_config_entry)

    mock_api_client.async_close_device.side_effect = FlussApiClientError("API Boom")

    with pytest.raises(HomeAssistantError) as exc_info:
        await hass.services.async_call(
            COVER_DOMAIN,
            SERVICE_CLOSE_COVER,
            {ATTR_ENTITY_ID: "cover.device_1"},
            blocking=True,
        )

    assert exc_info.value.translation_domain == "fluss"
    assert exc_info.value.translation_key == "close_failed"
    assert exc_info.value.translation_placeholders == {"error": "API Boom"}


async def test_cover_state_closed(
    hass: HomeAssistant,
    mock_api_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test cover reports closed state from openCloseStatus."""
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get("cover.device_1")
    assert state is not None
    assert state.state == "closed"


async def test_cover_state_open(
    hass: HomeAssistant,
    mock_api_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test cover reports open state from openCloseStatus."""
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get("cover.device_2")
    assert state is not None
    assert state.state == "open"


async def test_cover_state_unknown_when_status_unavailable(
    hass: HomeAssistant,
    mock_api_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test that no covers are created when the status API fails."""
    mock_api_client.async_get_device_status.side_effect = FlussApiClientError(
        "Status unavailable"
    )

    await setup_integration(hass, mock_config_entry)

    assert hass.states.get("cover.device_1") is None
    assert hass.states.get("cover.device_2") is None


async def test_no_cover_when_status_missing(
    hass: HomeAssistant,
    mock_api_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test that covers are not created when openCloseStatus is missing."""
    mock_api_client.async_get_device_status.side_effect = None
    mock_api_client.async_get_device_status.return_value = {"status": {}}

    await setup_integration(hass, mock_config_entry)

    assert hass.states.get("cover.device_1") is None
    assert hass.states.get("cover.device_2") is None


async def test_cover_state_unknown_on_unexpected_status(
    hass: HomeAssistant,
    mock_api_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test cover reports unknown when the API returns an unrecognized status."""
    await setup_integration(hass, mock_config_entry)

    mock_api_client.async_get_device_status.side_effect = lambda device_id: {
        "status": {"deviceId": device_id, "openCloseStatus": "Moving"}
    }
    await hass.services.async_call(
        COVER_DOMAIN,
        SERVICE_OPEN_COVER,
        {ATTR_ENTITY_ID: "cover.device_1"},
        blocking=True,
    )
    async_fire_time_changed(
        hass, dt_util.utcnow() + timedelta(seconds=STATUS_REFRESH_DELAY + 1)
    )
    await hass.async_block_till_done()

    state = hass.states.get("cover.device_1")
    assert state is not None
    assert state.state == STATE_UNKNOWN


async def test_cover_open_schedules_delayed_refresh(
    hass: HomeAssistant,
    mock_api_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test opening a cover schedules a delayed coordinator refresh."""
    await setup_integration(hass, mock_config_entry)

    mock_api_client.async_get_devices.reset_mock()

    await hass.services.async_call(
        COVER_DOMAIN,
        SERVICE_OPEN_COVER,
        {ATTR_ENTITY_ID: "cover.device_1"},
        blocking=True,
    )

    assert mock_api_client.async_get_devices.call_count == 0

    async_fire_time_changed(
        hass, dt_util.utcnow() + timedelta(seconds=STATUS_REFRESH_DELAY + 1)
    )
    await hass.async_block_till_done()

    assert mock_api_client.async_get_devices.call_count >= 1
