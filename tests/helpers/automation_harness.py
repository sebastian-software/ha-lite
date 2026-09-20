"""Test-only harness for exercising the retained automation runtime helpers.

The Automation product integration is intentionally absent from ha-lite. Component
runtime tests still need a small orchestrator to wire retained triggers,
conditions, and actions together without restoring that product integration.
"""

import logging
from typing import Any

from homeassistant.const import SERVICE_TURN_OFF
from homeassistant.core import Context, HomeAssistant, ServiceCall
from homeassistant.helpers import (
    condition as condition_helper,
    config_validation as cv,
    script as script_helper,
    trigger as trigger_helper,
)
from homeassistant.helpers.typing import ConfigType

DOMAIN = "automation"

_LOGGER = logging.getLogger(__name__)
_DATA = "ha_lite_test_automation_harness"


def _log(level: int, message: str, **kwargs: Any) -> None:
    """Forward retained trigger setup messages to the test log."""
    _LOGGER.log(level, message, **kwargs)


def async_mock_service(
    hass: HomeAssistant, service: str, handler: Any
) -> None:
    """Register a test-owned harness service without product translations."""
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


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Wire automation-shaped test config to retained runtime primitives."""
    raw_items = config.get(DOMAIN, [])
    items = raw_items if isinstance(raw_items, list) else [raw_items]
    data = hass.data.setdefault(_DATA, {"removes": [], "scripts": []})

    if not hass.services.has_service(DOMAIN, SERVICE_TURN_OFF):

        async def async_turn_off(_call: ServiceCall) -> None:
            await _async_detach(hass)

        async_mock_service(hass, SERVICE_TURN_OFF, async_turn_off)

    for index, item in enumerate(items):
        trigger_config = cv.TRIGGER_SCHEMA(item.get("triggers", item.get("trigger")))
        trigger_config = await trigger_helper.async_validate_trigger_config(
            hass, trigger_config
        )

        action_config = cv.SCRIPT_SCHEMA(item.get("actions", item.get("action")))
        action_config = await script_helper.async_validate_actions_config(
            hass, action_config
        )
        action_script = script_helper.Script(
            hass,
            action_config,
            f"retained runtime test {index}",
            DOMAIN,
        )
        data["scripts"].append(action_script)

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

        async def async_action(
            variables: dict[str, Any],
            context: Context | None = None,
            *,
            action_script: script_helper.Script = action_script,
            conditions=conditions,
        ) -> None:
            for condition in conditions:
                if not condition.async_check(variables=variables):
                    return
            await action_script.async_run(variables, context or Context())

        remove = await trigger_helper.async_initialize_triggers(
            hass,
            trigger_config,
            async_action,
            DOMAIN,
            f"retained runtime test {index}",
            _log,
        )
        if remove is not None:
            data["removes"].append(remove)

    return True
