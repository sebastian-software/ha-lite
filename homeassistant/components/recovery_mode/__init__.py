"""The Recovery Mode integration."""

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

DOMAIN = "recovery_mode"

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Recovery Mode component."""
    persistent_notification.async_create(
        hass,
        (
            "Running in recovery mode. The error log is available over the"
            " WebSocket API (system_log/list) and in home-assistant.log."
        ),
        "Recovery Mode",
    )
    return True
