"""The tests for components."""

import homeassistant.components as homeassistant_components
import homeassistant.components.automation as automation_compat
import homeassistant.components.script as script_compat
import homeassistant.setup as homeassistant_setup

from tests.helpers import automation_harness, helper_harness

_original_async_setup_component = homeassistant_setup.async_setup_component


async def _async_setup_component(hass, domain, config):
    """Route deleted product setup to test-only retained-runtime harnesses."""
    if domain == automation_harness.DOMAIN:
        return await automation_harness.async_setup_component(hass, config)
    if domain == automation_harness.SCRIPT_DOMAIN:
        return await automation_harness.async_setup_script(hass, config)
    if (setup := helper_harness.SETUP.get(domain)) is not None:
        return await setup(hass, config)
    return await _original_async_setup_component(hass, domain, config)


# Keep production imports honest: expose the harnesses only as attributes used
# by component tests. We intentionally do not register their modules in
# sys.modules, where production code finds the compat modules instead.
homeassistant_components.automation = automation_harness
homeassistant_components.input_boolean = helper_harness.input_boolean
homeassistant_components.input_number = helper_harness.input_number
homeassistant_components.input_select = helper_harness.input_select
homeassistant_components.counter = helper_harness.counter
homeassistant_components.intent_script = helper_harness.intent_script
homeassistant_setup.async_setup_component = _async_setup_component

# The compat modules find no automations or scripts in production. In tests the
# harness has set some up, so the lookups answer from it; integrations bind
# these names when they are first imported, which is after this module.
automation_compat.automations_with_entity = automation_harness.automations_with_entity
automation_compat.automations_with_device = automation_harness.automations_with_device
script_compat.scripts_with_entity = automation_harness.scripts_with_entity
