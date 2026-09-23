"""Compatibility module for the removed Onboarding product integration.

This is deliberately not a Home Assistant integration: it has no manifest and no
setup entry point. Config flows ask it whether the instance has been set up,
to confirm discovered devices automatically during the browser wizard. ha-lite
has no wizard (ADR 0016), so the instance always counts as onboarded, which is
also what upstream answers when onboarding is not loaded.
"""

from homeassistant.core import HomeAssistant, callback

DOMAIN = "onboarding"


@callback
def async_is_onboarded(hass: HomeAssistant) -> bool:
    """Return if Home Assistant has been onboarded."""
    return True


@callback
def async_is_user_onboarded(hass: HomeAssistant) -> bool:
    """Return if a user has been created as part of onboarding."""
    return True
