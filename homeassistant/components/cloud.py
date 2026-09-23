"""Compatibility module for the removed Home Assistant Cloud integration.

This is deliberately not a Home Assistant integration: it has no manifest and no
setup entry point. Integrations ask it whether Home Assistant Cloud can give
them a public webhook URL. It answers as upstream does when nobody is logged
in: no subscription, no connection, no cloudhook. The integrations then use
their local webhook URL.
"""

from collections.abc import Awaitable, Callable
from enum import Enum
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.util.signal_type import SignalType

DOMAIN = "cloud"


class CloudNotAvailable(HomeAssistantError):
    """Raised when an action requires the cloud but it's not available."""


class CloudNotConnected(CloudNotAvailable):
    """Raised when an action requires the cloud but it's not connected."""


class CloudConnectionState(Enum):
    """Cloud connection state."""

    CLOUD_CONNECTED = "cloud_connected"
    CLOUD_DISCONNECTED = "cloud_disconnected"


# Upstream's signals; nothing in ha-lite sends them.
SIGNAL_CLOUD_CONNECTION_STATE: SignalType[CloudConnectionState] = SignalType(
    "CLOUD_CONNECTION_STATE"
)
_SIGNAL_CLOUDHOOKS_UPDATED: SignalType[dict[str, Any]] = SignalType(
    "CLOUDHOOKS_UPDATED"
)


@callback
def async_is_logged_in(hass: HomeAssistant) -> bool:
    """Return if a user is logged in; ha-lite has no cloud account."""
    return False


@callback
def async_is_connected(hass: HomeAssistant) -> bool:
    """Return if connected to the cloud; ha-lite never is."""
    return False


@callback
def async_active_subscription(hass: HomeAssistant) -> bool:
    """Return if there is an active subscription; ha-lite has none."""
    return False


@callback
def async_listen_connection_change(
    hass: HomeAssistant,
    target: Callable[[CloudConnectionState], Awaitable[None] | None],
) -> Callable[[], None]:
    """Notify on connection state changes."""
    return async_dispatcher_connect(hass, SIGNAL_CLOUD_CONNECTION_STATE, target)


@callback
def async_listen_cloudhook_change(
    hass: HomeAssistant,
    webhook_id: str,
    on_change: Callable[[dict[str, Any] | None], None],
) -> Callable[[], None]:
    """Notify when the cloudhook of the given webhook changes."""

    @callback
    def _handle_cloudhooks_updated(cloudhooks: dict[str, Any]) -> None:
        on_change(cloudhooks.get(webhook_id))

    return async_dispatcher_connect(
        hass, _SIGNAL_CLOUDHOOKS_UPDATED, _handle_cloudhooks_updated
    )


async def async_create_cloudhook(hass: HomeAssistant, webhook_id: str) -> str:
    """Create a cloudhook; impossible without a connection."""
    raise CloudNotConnected


async def async_get_or_create_cloudhook(hass: HomeAssistant, webhook_id: str) -> str:
    """Get or create a cloudhook; impossible without a connection."""
    raise CloudNotConnected


async def async_delete_cloudhook(hass: HomeAssistant, webhook_id: str) -> None:
    """Delete a cloudhook; there is none."""
    raise CloudNotAvailable
