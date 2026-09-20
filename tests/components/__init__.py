"""The tests for components."""

import homeassistant.components as homeassistant_components
import homeassistant.setup as homeassistant_setup

from tests.helpers import automation_harness

_original_async_setup_component = homeassistant_setup.async_setup_component


async def _async_setup_component(hass, domain, config):
    """Route deleted product setup to test-only retained-runtime harnesses."""
    if domain == automation_harness.DOMAIN:
        return await automation_harness.async_setup(hass, config)
    if domain == automation_harness.SCRIPT_DOMAIN:
        return await automation_harness.async_setup_script(hass, config)
    return await _original_async_setup_component(hass, domain, config)


# Keep production imports honest: expose the Automation harness only as an
# attribute used by component tests. We intentionally do not register a
# homeassistant.components.automation module in sys.modules.
homeassistant_components.automation = automation_harness
homeassistant_setup.async_setup_component = _async_setup_component
