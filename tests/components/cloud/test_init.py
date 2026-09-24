"""Test the cloud integration, reduced to account linking.

test_account_link.py is upstream's and patches hass_nabucasa's account_link
functions. These tests run them for real against what ha-lite stores in place
of a hass_nabucasa Cloud.
"""

import asyncio
from collections.abc import Awaitable, Callable
import logging
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from homeassistant import config_entries
from homeassistant.components import cloud
from homeassistant.components.cloud import account_link
from homeassistant.components.cloud.const import DATA_CLOUD, DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import OAuth2TokenRequestReauthError
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.setup import async_setup_component

from tests.common import mock_platform
from tests.test_util.aiohttp import AiohttpClientMocker

SERVER = "https://account-link.nabucasa.com"
TEST_DOMAIN = "oauth2_test"


@pytest.fixture
async def setup_cloud(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """Set up the cloud integration with a session the mocker answers."""
    assert await async_setup_component(hass, DOMAIN, {DOMAIN: {}})


@pytest.mark.usefixtures("setup_cloud")
async def test_provides_implementation(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test the services come from the account link server."""
    aioclient_mock.get(
        f"{SERVER}/services", json=[{"service": TEST_DOMAIN, "min_version": "0.1.0"}]
    )

    implementations = await config_entry_oauth2_flow.async_get_implementations(
        hass, TEST_DOMAIN
    )

    assert implementations[DOMAIN].service == TEST_DOMAIN
    assert await config_entry_oauth2_flow.async_get_implementations(hass, "other") == {}


@pytest.mark.usefixtures("setup_cloud", "current_request_with_host")
async def test_authorize(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test a config flow receives the tokens through the account link server."""
    aioclient_mock.get(
        f"{SERVER}/services", json=[{"service": TEST_DOMAIN, "min_version": "0.1.0"}]
    )
    mock_platform(hass, f"{TEST_DOMAIN}.config_flow")

    class TestFlowHandler(config_entry_oauth2_flow.AbstractOAuth2FlowHandler):
        """Test flow handler."""

        DOMAIN = TEST_DOMAIN

        @property
        def logger(self) -> logging.Logger:
            """Return logger."""
            return logging.getLogger(__name__)

    tokens = {
        "refresh_token": "mock-refresh",
        "access_token": "mock-access",
        "expires_in": 10,
        "token_type": "bearer",
    }
    responses: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    responses.put_nowait({"authorize_url": "https://example.com/auth"})
    websocket = AsyncMock()
    websocket.receive_json = responses.get

    with (
        patch.dict(config_entries.HANDLERS, {TEST_DOMAIN: TestFlowHandler}),
        patch(
            "aiohttp.ClientSession.ws_connect", AsyncMock(return_value=websocket)
        ) as ws_connect,
    ):
        result = await hass.config_entries.flow.async_init(
            TEST_DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] is FlowResultType.EXTERNAL_STEP
        assert result["url"] == "https://example.com/auth"

        # The user authorizes at the vendor; the server sends the tokens.
        responses.put_nowait({"tokens": tokens})
        await hass.async_block_till_done(wait_background_tasks=True)

        result = await hass.config_entries.flow.async_configure(result["flow_id"])

    ws_connect.assert_awaited_once_with(f"{SERVER}/v1")
    websocket.send_json.assert_awaited_once_with({"service": TEST_DOMAIN})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["auth_implementation"] == DOMAIN
    assert result["data"]["token"]["access_token"] == "mock-access"


@pytest.mark.usefixtures("setup_cloud")
async def test_refresh_token(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test tokens are refreshed through the account link server."""
    aioclient_mock.post(
        f"{SERVER}/refresh_token/{TEST_DOMAIN}", json={"access_token": "new-access"}
    )
    implementation = account_link.CloudOAuth2Implementation(hass, TEST_DOMAIN)

    token = await implementation._async_refresh_token(
        {"refresh_token": "mock-refresh", "access_token": "old-access"}
    )

    assert token == {
        "refresh_token": "mock-refresh",
        "access_token": "new-access",
        "service": TEST_DOMAIN,
    }
    assert aioclient_mock.mock_calls[0][2] == {"refresh_token": "mock-refresh"}


@pytest.mark.usefixtures("setup_cloud")
async def test_refresh_token_rejected(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test a rejected refresh token asks for reauthentication."""
    aioclient_mock.post(f"{SERVER}/refresh_token/{TEST_DOMAIN}", status=400)
    implementation = account_link.CloudOAuth2Implementation(hass, TEST_DOMAIN)

    with pytest.raises(OAuth2TokenRequestReauthError):
        await implementation._async_refresh_token(
            {"refresh_token": "mock-refresh", "access_token": "old-access"}
        )


async def test_upstream_options_are_ignored(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    """Test a configuration carried over from Home Assistant still sets up."""
    assert await async_setup_component(
        hass, DOMAIN, {DOMAIN: {"alexa": {}, "google_actions": {}}}
    )

    assert hass.data[DATA_CLOUD].account_link_server == "account-link.nabucasa.com"
    assert "does not support any configuration parameters" in caplog.text


@pytest.mark.parametrize(
    "answer",
    [
        cloud.async_is_logged_in,
        cloud.async_is_connected,
        cloud.async_active_subscription,
    ],
)
async def test_no_login(hass: HomeAssistant, answer: Callable[..., bool]) -> None:
    """Test the cloud answers as upstream does when nobody is logged in."""
    assert answer(hass) is False


@pytest.mark.parametrize(
    ("action", "error"),
    [
        (cloud.async_create_cloudhook, cloud.CloudNotConnected),
        (cloud.async_get_or_create_cloudhook, cloud.CloudNotConnected),
        (cloud.async_delete_cloudhook, cloud.CloudNotAvailable),
    ],
)
async def test_no_cloudhooks(
    hass: HomeAssistant,
    action: Callable[[HomeAssistant, str], Awaitable[Any]],
    error: type[Exception],
) -> None:
    """Test cloudhooks are unavailable, so integrations use their local URL."""
    with pytest.raises(error):
        await action(hass, "webhook_id")
