"""Test-only harnesses for retained Automation and Script runtime helpers.

The Automation and Script product integrations are intentionally absent from
ha-lite. Component runtime tests still need small orchestrators to exercise the
retained trigger, condition, and action primitives without restoring those
integrations.
"""

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config as conf_util
from homeassistant.const import SERVICE_RELOAD, SERVICE_TURN_OFF
from homeassistant.core import Context, HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import (
    condition as condition_helper,
    config_validation as cv,
    script as script_helper,
    trigger as trigger_helper,
)
from homeassistant.helpers.typing import ConfigType

DOMAIN = "automation"
SCRIPT_DOMAIN = "script"

_LOGGER = logging.getLogger(__name__)
_DATA = "ha_lite_test_automation_harness"
_SCRIPT_DATA = "ha_lite_test_script_harness"


def _log(level: int, message: str, **kwargs: Any) -> None:
    """Forward retained trigger setup messages to the test log."""
    _LOGGER.log(level, message, **kwargs)


def async_mock_service(hass: HomeAssistant, service: str, handler: Any) -> None:
    """Register a test-owned automation service without product translations."""
    hass.services.async_register(DOMAIN, service, handler)


async def _async_detach(hass: HomeAssistant) -> None:
    """Detach all triggers and stop action scripts created by the harness."""
    data = hass.data.get(_DATA)
    if data is None:
        return

    for remove in data["removes"]:
        remove()
    data["removes"].clear()

    for action_script in data["scripts"]:
        await action_script.async_stop()
    data["scripts"].clear()


async def _async_reload(hass: HomeAssistant) -> None:
    """Reload automation-shaped YAML into the retained runtime harness."""
    config = await conf_util.async_hass_config_yaml(hass)
    await _async_detach(hass)
    await async_setup(hass, config)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Wire automation-shaped test config to retained runtime primitives."""
    raw_items = config.get(DOMAIN, [])
    items = raw_items if isinstance(raw_items, list) else [raw_items]
    data = hass.data.setdefault(_DATA, {"removes": [], "scripts": []})

    if not hass.services.has_service(DOMAIN, SERVICE_TURN_OFF):

        async def async_turn_off(_call: ServiceCall) -> None:
            await _async_detach(hass)

        async_mock_service(hass, SERVICE_TURN_OFF, async_turn_off)

    if not hass.services.has_service(DOMAIN, SERVICE_RELOAD):

        async def async_reload(_call: ServiceCall) -> None:
            await _async_reload(hass)

        async_mock_service(hass, SERVICE_RELOAD, async_reload)

    for index, item in enumerate(items):
        name = item.get("alias") or f"automation {index}"

        try:
            trigger_config = cv.TRIGGER_SCHEMA(item.get("triggers", item.get("trigger")))
            trigger_config = await trigger_helper.async_validate_trigger_config(
                hass, trigger_config
            )

            action_config = cv.SCRIPT_SCHEMA(item.get("actions", item.get("action")))
            action_config = await script_helper.async_validate_actions_config(
                hass, action_config
            )

            conditions = []
            if (raw_conditions := item.get("conditions", item.get("condition"))) is not None:
                condition_config = cv.CONDITIONS_SCHEMA(raw_conditions)
                condition_config = await condition_helper.async_validate_conditions_config(
                    hass, condition_config
                )
                conditions = [
                    await condition_helper.async_from_config(hass, condition)
                    for condition in condition_config
                ]
        except (vol.Invalid, HomeAssistantError) as err:
            # The removed Automation integration treated per-item validation
            # failures as disabled automations instead of aborting setup for all
            # remaining items. Preserve that behavior in the test harness.
            _LOGGER.error(
                "Automation %s could not be prepared and has been disabled: %s",
                name,
                err,
            )
            continue

        action_script = script_helper.Script(hass, action_config, name, DOMAIN)
        data["scripts"].append(action_script)

        async def async_action(
            variables: dict[str, Any],
            context: Context | None = None,
            *,
            action_script: script_helper.Script = action_script,
            conditions=conditions,
        ) -> script_helper.ScriptRunResult | None:
            try:
                for condition in conditions:
                    if not condition.async_check(variables=variables):
                        return None

                parent_id = None if context is None else context.id
                trigger_context = Context(parent_id=parent_id)
                return await action_script.async_run(variables, trigger_context)
            except (vol.Invalid, HomeAssistantError):
                # Script already logs execution errors. The removed Automation
                # integration swallowed these so another matching trigger can
                # still provide a result, e.g. a Conversation response.
                return None

        remove = await trigger_helper.async_initialize_triggers(
            hass,
            trigger_config,
            async_action,
            DOMAIN,
            name,
            _log,
        )
        if remove is not None:
            data["removes"].append(remove)

    return True


async def async_setup_script(hass: HomeAssistant, config: ConfigType) -> bool:
    """Expose YAML script definitions as test-only services."""
    raw_scripts = config.get(SCRIPT_DOMAIN, {})
    if not isinstance(raw_scripts, dict):
        return True

    scripts = hass.data.setdefault(_SCRIPT_DATA, {})

    for service_name, item in raw_scripts.items():
        try:
            sequence = cv.SCRIPT_SCHEMA(item.get("sequence", []))
            sequence = await script_helper.async_validate_actions_config(
                hass, sequence
            )
        except (vol.Invalid, HomeAssistantError) as err:
            _LOGGER.error(
                "Script %s could not be prepared and has been disabled: %s",
                service_name,
                err,
            )
            continue

        action_script = script_helper.Script(hass, sequence, service_name, SCRIPT_DOMAIN)
        scripts[service_name] = action_script

        async def async_run_script(
            call: ServiceCall,
            *,
            action_script: script_helper.Script = action_script,
        ) -> None:
            await action_script.async_run(dict(call.data), call.context)

        hass.services.async_register(SCRIPT_DOMAIN, service_name, async_run_script)

    return True
