"""Home Assistant Cloud, reduced to account linking.

Some vendors give OAuth client credentials only to Nabu Casa, not to users:
August, Yale and Watts sign in through Nabu Casa's account link server, which
needs no Home Assistant Cloud account. ha-lite keeps that and nothing else of
the cloud: no login, remote access, cloudhooks, Alexa, Google Assistant, speech
or backup. The functions integrations call to ask for those answer as upstream
does when nobody is logged in, so the integrations use their local webhook URL.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

from aiohttp import ClientSession
from hass_nabucasa.const import DEFAULT_SERVERS

from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.typing import ConfigType
from homeassistant.util.signal_type import SignalType

from . import account_link
from .const import DATA_CLOUD, DOMAIN

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)


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


@dataclass(frozen=True)
class AccountLinkClient:
    """The part of a hass_nabucasa CloudClient that account linking uses."""

    websession: ClientSession


@dataclass(frozen=True)
class AccountLinkCloud:
    """The part of a hass_nabucasa Cloud that account linking uses.

    Building a real Cloud would build remote access, voice, Alexa and Google
    with it.
    """

    client: AccountLinkClient
    account_link_server: str = DEFAULT_SERVERS["production"]["account_link"]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Offer account linking as an OAuth2 implementation."""
    hass.data[DATA_CLOUD] = AccountLinkCloud(
        AccountLinkClient(async_get_clientsession(hass))
    )
    account_link.async_setup(hass)
    return True


@callback
def async_is_logged_in(hass: HomeAssistant) -> bool:
    """Return if a user is logged in; there is no login to Home Assistant Cloud."""
    return False


@callback
def async_is_connected(hass: HomeAssistant) -> bool:
    """Return if connected to the cloud; never, without a login."""
    return False


@callback
def async_active_subscription(hass: HomeAssistant) -> bool:
    """Return if there is an active subscription; never, without a login."""
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
