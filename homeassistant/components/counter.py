"""Compatibility module for the removed Counter helper.

This is deliberately not a Home Assistant integration: it has no manifest and no
setup entry point. Integrations name the domain in entity selectors, which
simply find no counters in ha-lite.
"""

DOMAIN = "counter"
