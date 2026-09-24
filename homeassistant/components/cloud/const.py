"""Constants for the Home Assistant Cloud integration."""

from typing import Any

from homeassistant.util.hass_dict import HassKey

DOMAIN = "cloud"

# Upstream stores a hass_nabucasa Cloud here. ha-lite stores only what
# hass_nabucasa's account_link functions read from one; see __init__.py.
DATA_CLOUD: HassKey[Any] = HassKey(DOMAIN)
