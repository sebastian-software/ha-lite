"""Compatibility module for the removed Input Button helper.

This is deliberately not a Home Assistant integration: it has no manifest and no
setup entry point. Integrations name the domain and its press action among the
domains they support, which simply find no input buttons in ha-lite.
"""

from .button import SERVICE_PRESS  # noqa: F401

DOMAIN = "input_button"
