"""Test the Matter config flow."""

from collections.abc import Generator
from ipaddress import ip_address
from unittest.mock import AsyncMock, patch

from matter_server.client.exceptions import CannotConnect, InvalidServerVersion
import pytest

from homeassistant import config_entries
from homeassistant.components.matter.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from tests.common import MockConfigEntry

ZEROCONF_INFO_TCP = ZeroconfServiceInfo(
    ip_address=ip_address("fd11:be53:8d46:0:729e:5a4f:539d:1ee6"),
    ip_addresses=[ip_address("fd11:be53:8d46:0:729e:5a4f:539d:1ee6")],
    port=5540,
    hostname="CDEFGHIJ12345678.local.",
    type="_matter._tcp.local.",
    name="ABCDEFGH123456789-0000000012345678._matter._tcp.local.",
    properties={"SII": "3300", "SAI": "1100", "T": "0"},
)

ZEROCONF_INFO_UDP = ZeroconfServiceInfo(
    ip_address=ip_address("fd11:be53:8d46:0:729e:5a4f:539d:1ee6"),
    ip_addresses=[ip_address("fd11:be53:8d46:0:729e:5a4f:539d:1ee6")],
    port=5540,
    hostname="CDEFGHIJ12345678.local.",
    type="_matterc._udp.local.",
    name="ABCDEFGH123456789._matterc._udp.local.",
    properties={
        "VP": "4874+77",
        "DT": "21",
        "DN": "Eve Door",
        "SII": "3300",
        "SAI": "1100",
        "T": "0",
        "D": "183",
        "CM": "2",
        "RI": "0400530980B950D59BF473CFE42BD7DDBF2D",
        "PH": "36",
        "PI": None,
    },
)


@pytest.fixture(name="setup_entry", autouse=True)
def setup_entry_fixture() -> Generator[AsyncMock]:
    """Mock entry setup."""
    with patch(
        "homeassistant.components.matter.async_setup_entry", return_value=True
    ) as mock_setup_entry:
        yield mock_setup_entry


@pytest.fixture(name="unload_entry", autouse=True)
def unload_entry_fixture() -> Generator[AsyncMock]:
    """Mock entry unload."""
    with patch(
        "homeassistant.components.matter.async_unload_entry", return_value=True
    ) as mock_unload_entry:
        yield mock_unload_entry


@pytest.fixture(name="client_connect", autouse=True)
def client_connect_fixture() -> Generator[AsyncMock]:
    """Mock server version."""
    with patch(
        "homeassistant.components.matter.config_flow.MatterClient.connect"
    ) as client_connect:
        yield client_connect


async def test_manual_create_entry(
    hass: HomeAssistant,
    client_connect: AsyncMock,
    setup_entry: AsyncMock,
) -> None:
    """Test user step create entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "url": "ws://localhost:5580/ws",
        },
    )
    await hass.async_block_till_done()

    assert client_connect.call_count == 1
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Matter"
    assert result["data"] == {"url": "ws://localhost:5580/ws"}
    assert setup_entry.call_count == 1


@pytest.mark.parametrize(
    ("error", "side_effect"),
    [
        ("cannot_connect", CannotConnect(Exception("Boom"))),
        ("invalid_server_version", InvalidServerVersion("Invalid version")),
        ("unknown", Exception("Unknown boom")),
    ],
)
async def test_manual_errors(
    hass: HomeAssistant,
    client_connect: AsyncMock,
    error: str,
    side_effect: Exception,
) -> None:
    """Test user step cannot connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    client_connect.side_effect = side_effect
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "url": "ws://localhost:5580/ws",
        },
    )

    assert client_connect.call_count == 1
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}


async def test_manual_already_configured(
    hass: HomeAssistant,
    client_connect: AsyncMock,
    setup_entry: AsyncMock,
) -> None:
    """Test manual step abort if already configured."""
    entry = MockConfigEntry(
        domain=DOMAIN, data={"url": "ws://host1:5581/ws"}, title="Matter"
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "url": "ws://localhost:5580/ws",
        },
    )
    await hass.async_block_till_done()

    assert client_connect.call_count == 1
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfiguration_successful"
    assert entry.data["url"] == "ws://localhost:5580/ws"
    assert entry.title == "Matter"
    assert setup_entry.call_count == 1


@pytest.mark.parametrize("zeroconf_info", [ZEROCONF_INFO_TCP, ZEROCONF_INFO_UDP])
async def test_zeroconf_discovery(
    hass: HomeAssistant,
    client_connect: AsyncMock,
    setup_entry: AsyncMock,
    zeroconf_info: ZeroconfServiceInfo,
) -> None:
    """Test flow started from Zeroconf discovery."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=zeroconf_info,
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "manual"
    assert result["errors"] is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "url": "ws://localhost:5580/ws",
        },
    )
    await hass.async_block_till_done()

    assert client_connect.call_count == 1
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Matter"
    assert result["data"] == {"url": "ws://localhost:5580/ws"}
    assert setup_entry.call_count == 1
