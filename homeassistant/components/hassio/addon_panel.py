"""Headless compatibility shims for obsolete Supervisor add-on panels."""

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback

from .coordinator import HassioMainDataUpdateCoordinator


def async_setup_addon_panel(hass: HomeAssistant) -> None:
    """Do not register Supervisor ingress panels in the headless runtime."""


@callback
def async_setup_addon_panel_coordinator(
    hass: HomeAssistant, coordinator: HassioMainDataUpdateCoordinator
) -> CALLBACK_TYPE:
    """Return a no-op unsubscribe callback for removed frontend panel syncing."""

    @callback
    def _unsubscribe() -> None:
        return

    return _unsubscribe
