"""Compatibility module for the removed Input Boolean helper.

This is deliberately not a Home Assistant integration: it has no manifest and no
setup entry point. Integrations name the domain in entity selectors and in the
domains they support, which simply find no input booleans in ha-lite.
"""

DOMAIN = "input_boolean"
