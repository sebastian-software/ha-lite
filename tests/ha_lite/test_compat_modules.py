"""Compat modules answer questions, but are never products.

ADR 0020 lets a removed layer leave a compat module behind: a single file that
answers what integrations ask the layer. These tests hold every declared compat
module to that: it is a plain module, it has no manifest, and nothing can set
it up.
"""

import importlib.util
import json
from pathlib import Path

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.loader import IntegrationNotFound, async_get_integration

ROOT = Path(__file__).resolve().parents[2]
COMPONENTS = ROOT / "homeassistant" / "components"
CONFIG = ROOT / "script" / "ha_lite_closure_config.json"
COMPAT_MODULES = tuple(json.loads(CONFIG.read_text(encoding="utf-8"))["compat_modules"])


@pytest.mark.parametrize("domain", COMPAT_MODULES)
async def test_compat_module_is_not_an_integration(
    hass: HomeAssistant, domain: str
) -> None:
    """A compat module can be imported, but the loader finds no integration."""
    spec = importlib.util.find_spec(f"homeassistant.components.{domain}")
    assert spec is not None
    assert spec.submodule_search_locations is None
    assert not (COMPONENTS / domain / "manifest.json").exists()
    with pytest.raises(IntegrationNotFound):
        await async_get_integration(hass, domain)
