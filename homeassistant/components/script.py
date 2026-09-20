"""Compatibility domain marker for the removed Script product integration.

This is deliberately not a Home Assistant integration: it has no manifest and no
setup entry point. Retained integrations may still need to classify existing
``script.*`` entity/service references without importing the deleted product.
"""

DOMAIN = "script"

# Legacy constants still imported by retained helpers/integrations. Keeping them
# here does not restore the Script integration or its setup/service surface.
from homeassistant.const import CONF_MODE, CONF_SEQUENCE  # noqa: E402,F401
