"""Compatibility domain marker for the removed Script product integration.

This is deliberately not a Home Assistant integration: it has no manifest and no
setup entry point. Retained integrations may still need to classify existing
``script.*`` entity/service references without importing the deleted product.
"""

from homeassistant.core import HomeAssistant, callback

DOMAIN = "script"

# Legacy constants still imported by retained helpers/integrations. Keeping them
# here does not restore the Script integration or its setup/service surface.
from homeassistant.const import CONF_MODE, CONF_SEQUENCE  # noqa: E402,F401


@callback
def scripts_with_entity(hass: HomeAssistant, entity_id: str) -> list[str]:
    """Return the scripts that reference an entity; ha-lite runs none."""
    return []
