"""Bootstrap is headless: recovery mode is an API path.

Upstream recovery mode boots the browser product. ha-lite's used to reach HTTP
only because backup, its one default, depended on it. It now sets up the API
surface on purpose, and says why it started in a log an API client can read.
"""

from collections.abc import Generator
from typing import Any
from unittest.mock import patch

import pytest

from homeassistant import bootstrap, runner
from homeassistant.components.system_log import DOMAIN as SYSTEM_LOG_DOMAIN
from homeassistant.exceptions import HomeAssistantError

from tests.common import get_test_config_dir


@pytest.fixture(autouse=True)
def mock_environment() -> Generator[None]:
    """Keep bootstrap away from logging setup, pip, sockets and the config dir."""
    with (
        patch("homeassistant.bootstrap.async_enable_logging"),
        patch("homeassistant.bootstrap.is_virtual_env", return_value=False),
        patch("homeassistant.bootstrap.async_mount_local_lib_path"),
        patch("homeassistant.config.process_ha_config_upgrade"),
        patch("homeassistant.config.async_ensure_config_exists", return_value=True),
        patch("homeassistant.util.package.is_installed", return_value=True),
        patch("homeassistant.components.http.HomeAssistantHTTP.start"),
        patch("homeassistant.components.http.HomeAssistantHTTP.stop"),
    ):
        yield


@pytest.fixture(autouse=True)
def apply_mock_storage(hass_storage: dict[str, Any]) -> None:
    """Keep bootstrap's stores in memory."""


@pytest.fixture(autouse=True)
async def apply_stop_hass(stop_hass: None) -> None:
    """Stop the instances bootstrap creates outside the hass fixture."""


@pytest.fixture(autouse=True)
def disable_block_async_io(disable_block_async_io: None) -> None:
    """Undo bootstrap's loop protection after each test."""


async def test_broken_configuration_starts_an_api_recovery_mode() -> None:
    """A configuration.yaml that does not parse leaves the API reachable."""
    with patch(
        "homeassistant.config.async_hass_config_yaml",
        side_effect=HomeAssistantError("mapping values are not allowed here"),
    ):
        hass = await bootstrap.async_setup_hass(
            runner.RuntimeConfig(
                config_dir=get_test_config_dir(),
                verbose=False,
                log_rotate_days=10,
                log_file="",
                log_no_color=False,
                skip_pip=True,
                recovery_mode=False,
            ),
        )

    assert hass.config.recovery_mode
    assert set(hass.config.components) >= bootstrap.DEFAULT_INTEGRATIONS_RECOVERY_MODE
    messages = [
        message
        for entry in hass.data[SYSTEM_LOG_DOMAIN].records.to_list()
        for message in entry["message"]
    ]
    assert (
        "Running in recovery mode: Failed to parse configuration.yaml:"
        " mapping values are not allowed here"
    ) in messages
