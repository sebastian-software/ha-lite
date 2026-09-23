"""Compatibility module for the removed Input Select helper.

This is deliberately not a Home Assistant integration: it has no manifest and no
setup entry point. Integrations name the domain and its select action among the
domains they support, which simply find no input selects in ha-lite.
"""

from homeassistant.const import SERVICE_SELECT_OPTION  # noqa: F401

DOMAIN = "input_select"
