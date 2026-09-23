"""Test HomeKit initialization."""

from unittest.mock import patch

import pytest

from homeassistant.components.homekit.const import DOMAIN
from homeassistant.config_entries import SOURCE_ZEROCONF, ConfigEntryState
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component

from .util import PATH_HOMEKIT

from tests.common import MockConfigEntry


@pytest.mark.usefixtures("mock_async_zeroconf")
async def test_bridge_with_triggers(
    hass: HomeAssistant,
    hk_driver,
    demo_cleanup,
    entity_registry: er.EntityRegistry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test we can setup a bridge with triggers and we ignore numeric states.

    Since numeric states are not supported by HomeKit as they require
    an above or below additional configuration which we have no way
    to input, we ignore them.
    """
    assert await async_setup_component(hass, "homeassistant", {})
    assert await async_setup_component(hass, "demo", {"demo": {}})
    await hass.async_block_till_done()

    entry = entity_registry.async_get("cover.living_room_window")
    assert entry is not None
    device_id = entry.device_id

    entry = MockConfigEntry(
        domain=DOMAIN,
        source=SOURCE_ZEROCONF,
        data={
            "name": "HASS Bridge",
            "port": 12345,
        },
        options={
            "filter": {
                "exclude_domains": [],
                "exclude_entities": [],
                "include_domains": [],
                "include_entities": ["cover.living_room_window"],
            },
            "exclude_accessory_mode": True,
            "mode": "bridge",
            "devices": [device_id],
        },
    )
    entry.add_to_hass(hass)

    with (
        patch(
            "homeassistant.components.network.async_get_source_ip",
            return_value="1.2.3.4",
        ),
        patch(f"{PATH_HOMEKIT}.async_port_is_available", return_value=True),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
        await hass.async_block_till_done()

        assert entry.state is ConfigEntryState.LOADED
        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()

    assert (
        "requires additional inputs which are not supported by HomeKit" in caplog.text
    )
