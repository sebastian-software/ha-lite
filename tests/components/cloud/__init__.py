"""Tests for the cloud integration, reduced to account linking."""

from typing import Any

from homeassistant.components.cloud.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component


async def mock_cloud(hass: HomeAssistant, config: dict[str, Any] | None = None) -> None:
    """Set up the cloud integration.

    Catalog tests call this before they patch the cloud functions to reach
    their cloudhook code. Upstream's helper also initialized a hass_nabucasa
    Cloud; ha-lite's cloud has none.
    """
    # Upstream's helper set this up first, and the tests calling it rely on it.
    assert await async_setup_component(hass, "homeassistant", {})

    assert await async_setup_component(hass, DOMAIN, {DOMAIN: config or {}})
