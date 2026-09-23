"""Compatibility module for the removed Input Number helper.

This is deliberately not a Home Assistant integration: it has no manifest and no
setup entry point. Integrations name the domain, its attributes and its set
action among the domains they support, which simply find no input numbers in
ha-lite.
"""

DOMAIN = "input_number"

ATTR_VALUE = "value"
CONF_MIN = "min"
CONF_MAX = "max"
CONF_STEP = "step"
SERVICE_SET_VALUE = "set_value"
