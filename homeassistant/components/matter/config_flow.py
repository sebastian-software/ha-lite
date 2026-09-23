"""Config flow for Matter integration."""

from typing import Any, override

from matter_server.client import MatterClient
from matter_server.client.exceptions import CannotConnect, InvalidServerVersion
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import AbortFlow
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .const import DOMAIN, LOGGER

DEFAULT_URL = "ws://localhost:5580/ws"
DEFAULT_TITLE = "Matter"


def get_manual_schema(user_input: dict[str, Any]) -> vol.Schema:
    """Return a schema for the manual step."""
    default_url = user_input.get(CONF_URL, DEFAULT_URL)
    return vol.Schema({vol.Required(CONF_URL, default=default_url): str})


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """Validate the user input allows us to connect."""
    client = MatterClient(data[CONF_URL], aiohttp_client.async_get_clientsession(hass))
    await client.connect()


class MatterConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Matter.

    ha-lite connects to an external Matter Server by URL. Upstream can also
    install and run the server as a Home Assistant OS add-on; that path is gone.
    """

    VERSION = 1

    def __init__(self) -> None:
        """Set up flow instance."""
        self.ws_address: str | None = None

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        return await self.async_step_manual()

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a manual configuration."""
        if user_input is None:
            return self.async_show_form(
                step_id="manual", data_schema=get_manual_schema({})
            )

        errors = {}

        try:
            await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidServerVersion:
            errors["base"] = "invalid_server_version"
        except Exception:  # noqa: BLE001
            LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            self.ws_address = user_input[CONF_URL]

            return await self._async_create_entry_or_abort()

        return self.async_show_form(
            step_id="manual", data_schema=get_manual_schema(user_input), errors=errors
        )

    @override
    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """Handle zeroconf discovery."""
        return await self._async_step_discovery_without_unique_id()

    async def _async_create_entry_or_abort(self) -> ConfigFlowResult:
        """Return a config entry for the flow or abort if already configured."""
        assert self.ws_address is not None

        if existing_config_entries := self._async_current_entries():
            config_entry = existing_config_entries[0]
            self.hass.config_entries.async_update_entry(
                config_entry,
                data={**config_entry.data, CONF_URL: self.ws_address},
                title=DEFAULT_TITLE,
            )
            await self.hass.config_entries.async_reload(config_entry.entry_id)
            raise AbortFlow("reconfiguration_successful")

        # Abort any other flows that may be in progress
        for progress in self._async_in_progress():
            self.hass.config_entries.flow.async_abort(progress["flow_id"])

        return self.async_create_entry(
            title=DEFAULT_TITLE, data={CONF_URL: self.ws_address}
        )
