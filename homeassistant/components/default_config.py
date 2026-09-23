"""Compatibility module for the removed Default Config integration.

This is deliberately not a Home Assistant integration: it has no manifest and no
setup entry point. go2rtc checks whether `default_config:` is configured to
decide whether to set itself up. ha-lite has no such bundle (ADR 0016), so
go2rtc starts only when `go2rtc:` is configured.
"""

DOMAIN = "default_config"
