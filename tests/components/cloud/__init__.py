"""Test-only stand-in for the removed cloud integration's test helpers.

ha-lite keeps `homeassistant/components/cloud.py` as a compat module, not the
integration (ADR 0020). Catalog tests call `mock_cloud` before they patch the
cloud functions to reach their cloudhook code. With the compat module there is
no cloud to set up, so the stand-in sets up only what upstream's helper
required first.
"""

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component


async def mock_cloud(hass: HomeAssistant, config: dict[str, Any] | None = None) -> None:
    """Prepare the instance the way upstream's cloud helper did."""
    assert await async_setup_component(hass, "homeassistant", {})
