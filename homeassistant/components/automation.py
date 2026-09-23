"""Compatibility module for the removed Automation product integration.

This is deliberately not a Home Assistant integration: it has no manifest and no
setup entry point. Integrations ask it which automations use one of their
entities or devices, for example before they deprecate an entity, and in
ha-lite the answer is always none.
"""

from homeassistant.core import HomeAssistant, callback

DOMAIN = "automation"


@callback
def automations_with_entity(hass: HomeAssistant, entity_id: str) -> list[str]:
    """Return the automations that reference an entity; ha-lite runs none."""
    return []


@callback
def automations_with_device(hass: HomeAssistant, device_id: str) -> list[str]:
    """Return the automations that reference a device; ha-lite runs none."""
    return []
