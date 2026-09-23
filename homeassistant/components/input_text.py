"""Compatibility module for the removed Input Text helper.

This is deliberately not a Home Assistant integration: it has no manifest and no
setup entry point. Integrations name the domain in entity selectors, which
simply find no input texts in ha-lite.
"""

DOMAIN = "input_text"
