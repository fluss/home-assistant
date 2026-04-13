"""Config flow for Fluss+ integration."""

from __future__ import annotations

from typing import Any

from fluss_api import (
    FlussApiClient,
    FlussApiClientAuthenticationError,
    FlussApiClientCommunicationError,
)
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_API_KEY, UnitOfTime
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)

from .const import (
    CONF_SCAN_INTERVAL_STATUS,
    DEFAULT_SCAN_INTERVAL_STATUS_MINUTES,
    DOMAIN,
    LOGGER,
    MIN_SCAN_INTERVAL_MINUTES,
)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): cv.string,
        vol.Required(
            CONF_SCAN_INTERVAL_STATUS,
            default=DEFAULT_SCAN_INTERVAL_STATUS_MINUTES,
        ): NumberSelector(
            NumberSelectorConfig(
                min=MIN_SCAN_INTERVAL_MINUTES,
                step=1,
                mode=NumberSelectorMode.BOX,
                unit_of_measurement=UnitOfTime.MINUTES,
            )
        ),
    }
)


class FlussConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Fluss+."""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""

        errors: dict[str, str] = {}
        if user_input is not None:
            api_key = user_input[CONF_API_KEY]
            self._async_abort_entries_match({CONF_API_KEY: api_key})
            client = FlussApiClient(
                user_input[CONF_API_KEY], session=async_get_clientsession(self.hass)
            )
            try:
                await client.async_get_devices()
            except FlussApiClientCommunicationError:
                errors["base"] = "cannot_connect"
            except FlussApiClientAuthenticationError:
                errors["base"] = "invalid_auth"
            except Exception:  # noqa: BLE001
                LOGGER.exception("Unexpected exception occurred")
                errors["base"] = "unknown"
            if not errors:
                return self.async_create_entry(
                    title="My Fluss+ Devices", data=user_input
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
