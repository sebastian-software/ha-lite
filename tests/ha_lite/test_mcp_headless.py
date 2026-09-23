"""MCP works as a headless control surface.

ADR 0009 keeps the official MCP server as a core capability; ADR 0007 and the
Wave 3 cuts remove the browser, voice and AI products around it. The upstream
`mcp_server` suite passes in a reduced tree, but nothing in it says what the
tree must not contain. These tests do: the products are absent, and a real MCP
session loads nothing the retained closure does not contain.
"""

import importlib.util
import json
from pathlib import Path

import mcp.client.session
import mcp.client.streamable_http
import pytest

from homeassistant.components.homeassistant.exposed_entities import async_expose_entity
from homeassistant.components.mcp_server import DOMAIN as MCP_SERVER_DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_LLM_HASS_API, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers import llm
from homeassistant.helpers.httpx_client import create_async_httpx_client
from homeassistant.setup import async_setup_component

from tests.common import MockConfigEntry, setup_test_component_platform
from tests.components.light.common import MockLight
from tests.typing import ClientSessionGenerator

ROOT = Path(__file__).resolve().parents[2]
COMPONENTS = ROOT / "homeassistant" / "components"
CLOSURE = ROOT / "docs" / "architecture" / "retained-closure.json"

REMOVED_PRODUCTS = (
    "ai_task",
    "assist_pipeline",
    "assist_satellite",
    "frontend",
    "lovelace",
    "stt",
    "tts",
    "wake_word",
)

# The path external MCP clients are configured with.
MCP_ENDPOINT = "/api/mcp"
TEST_ENTITY = "light.kitchen"


@pytest.mark.parametrize("domain", REMOVED_PRODUCTS)
def test_removed_product_is_absent(domain: str) -> None:
    """A removed product cannot be imported, so nothing can lean on it."""
    assert importlib.util.find_spec(f"homeassistant.components.{domain}") is None


async def test_mcp_round_trip_stays_inside_the_closure(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    hass_access_token: str,
) -> None:
    """Initialize, list tools and act on a device, loading only retained code."""
    assert await async_setup_component(hass, "homeassistant", {})
    light = MockLight("Kitchen Light", STATE_OFF)
    light.entity_id = TEST_ENTITY
    light.unique_id = "kitchen-light"
    setup_test_component_platform(hass, "light", [light])
    assert await async_setup_component(hass, "light", {"light": [{"platform": "test"}]})
    await hass.async_block_till_done()
    async_expose_entity(hass, "conversation", TEST_ENTITY, True)

    entry = MockConfigEntry(
        domain=MCP_SERVER_DOMAIN, data={CONF_LLM_HASS_API: [llm.LLM_API_ASSIST]}
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.LOADED

    client = await hass_client()
    http_client = create_async_httpx_client(
        hass, headers={"Authorization": f"Bearer {hass_access_token}"}
    )
    async with (
        mcp.client.streamable_http.streamable_http_client(
            str(client.make_url(MCP_ENDPOINT)), http_client=http_client
        ) as (read_stream, write_stream, _),
        mcp.client.session.ClientSession(read_stream, write_stream) as session,
    ):
        await session.initialize()
        tools = await session.list_tools()
        assert "intent__HassTurnOn" in {tool.name for tool in tools.tools}
        result = await session.call_tool(
            name="intent__HassTurnOn", arguments={"name": "kitchen light"}
        )

    assert not result.isError
    assert hass.states.get(TEST_ENTITY).state == STATE_ON

    closure = set(json.loads(CLOSURE.read_text(encoding="utf-8"))["closure"])
    loaded = {
        domain
        for domain in hass.config.top_level_components
        if (COMPONENTS / domain / "manifest.json").is_file()
    }
    assert loaded - closure == set()
