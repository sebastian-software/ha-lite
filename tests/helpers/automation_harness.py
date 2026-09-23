"""Test-only harnesses for retained Automation and Script runtime helpers.

The Automation and Script product integrations are intentionally absent from
ha-lite. Component runtime tests still need small orchestrators to exercise the
retained trigger, condition, and action primitives without restoring those
integrations.

In production the compat modules answer that no automation or script
references anything. Here the harness answers from what it set up, so tests
that deprecate an entity in use see the automations and scripts using it.
"""

from collections.abc import Callable
import logging
from typing import Any

import voluptuous as vol
from voluptuous.humanize import humanize_error

from homeassistant import config as conf_util
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_RELOAD,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
)
from homeassistant.core import (
    Context,
    HomeAssistant,
    ServiceCall,
    callback,
    split_entity_id,
)
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import (
    condition as condition_helper,
    config_validation as cv,
    entity_registry as er,
    script as script_helper,
    trigger as trigger_helper,
)
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import slugify

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


def _register(
    hass: HomeAssistant, domain: str, unique_id: str | None, object_id: str, name: str
) -> str:
    """Return the entity id, registered under its unique id when it has one."""
    if unique_id is None:
        return f"{domain}.{object_id}"
    return (
        er.async_get(hass)
        .async_get_or_create(
            domain,
            domain,
            unique_id,
            suggested_object_id=object_id,
            original_name=name,
        )
        .entity_id
    )


def _publish(
    hass: HomeAssistant,
    name: str,
    item: ConfigType,
    state: str,
    references: Callable[[], tuple[set[str], set[str]]] | None = None,
) -> None:
    """Show the automation as an entity, as the removed integration did.

    Upstream tests count automation entities and read their state: on once
    armed, unavailable when the configuration failed validation.
    """
    entity_id = _register(hass, DOMAIN, item.get("id"), slugify(name), name)
    attributes = {"friendly_name": name, "id": item.get("id")}
    hass.states.async_set(entity_id, state, attributes)
    hass.data[_DATA]["entities"].add(entity_id)
    if references is not None:
        hass.data[_DATA]["references"][entity_id] = references


def _with_reference(hass: HomeAssistant, key: str, index: int, ref: str) -> list[str]:
    """Return the entity ids whose (entities, devices) references contain ref."""
    if (data := hass.data.get(key)) is None:
        return []
    return [
        entity_id
        for entity_id, references in data["references"].items()
        if ref in references()[index]
    ]


@callback
def automations_with_entity(hass: HomeAssistant, entity_id: str) -> list[str]:
    """Return the harness automations that reference an entity."""
    return _with_reference(hass, _DATA, 0, entity_id)


@callback
def automations_with_device(hass: HomeAssistant, device_id: str) -> list[str]:
    """Return the harness automations that reference a device."""
    return _with_reference(hass, _DATA, 1, device_id)


@callback
def scripts_with_entity(hass: HomeAssistant, entity_id: str) -> list[str]:
    """Return the harness scripts that reference an entity."""
    return _with_reference(hass, _SCRIPT_DATA, 0, entity_id)


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


async def async_setup_component(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up automations once, as a second setup of a real domain does nothing."""
    if _DATA in hass.data:
        return True
    return await async_setup(hass, config)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Wire automation-shaped test config to retained runtime primitives."""
    items = [
        platform_config
        for _, platform_config in conf_util.config_per_platform(config, DOMAIN)
    ]
    data = hass.data.setdefault(
        _DATA,
        {
            "removes": [],
            "scripts": [],
            "config": None,
            "entities": set(),
            "references": {},
        },
    )
    data["references"].clear()
    # turn_on re-arms from the config the test passed in, which reload cannot
    # do: these tests never write a YAML file for it to re-read.
    data["config"] = config

    if not hass.services.has_service(DOMAIN, SERVICE_TURN_OFF):

        async def async_turn_off(_call: ServiceCall) -> None:
            await _async_detach(hass)
            for entity_id in hass.data[_DATA]["entities"]:
                if (state := hass.states.get(entity_id)) is not None:
                    hass.states.async_set(entity_id, STATE_OFF, state.attributes)

        async_mock_service(hass, SERVICE_TURN_OFF, async_turn_off)

    if not hass.services.has_service(DOMAIN, SERVICE_TURN_ON):

        async def async_turn_on(_call: ServiceCall) -> None:
            await _async_detach(hass)
            if (stored := hass.data[_DATA]["config"]) is not None:
                await async_setup(hass, stored)

        async_mock_service(hass, SERVICE_TURN_ON, async_turn_on)

    if not hass.services.has_service(DOMAIN, SERVICE_RELOAD):

        async def async_reload(_call: ServiceCall) -> None:
            await _async_reload(hass)

        async_mock_service(hass, SERVICE_RELOAD, async_reload)

    for index, item in enumerate(items):
        name = item.get("alias") or f"automation {index}"

        try:
            trigger_config = cv.TRIGGER_SCHEMA(
                item.get("triggers", item.get("trigger"))
            )
            trigger_config = await trigger_helper.async_validate_trigger_config(
                hass, trigger_config
            )

            action_config = cv.SCRIPT_SCHEMA(item.get("actions", item.get("action")))
            action_config = await script_helper.async_validate_actions_config(
                hass, action_config
            )

            conditions = []
            condition_config = []
            if (
                raw_conditions := item.get("conditions", item.get("condition"))
            ) is not None:
                condition_config = cv.CONDITIONS_SCHEMA(raw_conditions)
                condition_config = (
                    await condition_helper.async_validate_conditions_config(
                        hass, condition_config
                    )
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
                humanize_error(item, err) if isinstance(err, vol.Invalid) else err,
            )
            _publish(hass, name, item, STATE_UNAVAILABLE)
            continue
        except Exception:
            # A platform's own validation can raise anything; the removed
            # Automation integration logged it with its traceback and went on.
            _LOGGER.exception("Unexpected error validating automation %s", name)
            _publish(hass, name, item, STATE_UNAVAILABLE)
            continue

        action_script = script_helper.Script(hass, action_config, name, DOMAIN)
        data["scripts"].append(action_script)

        async def async_action(
            variables: dict[str, Any],
            context: Context | None = None,
            *,
            action_script: script_helper.Script = action_script,
            conditions=tuple(conditions),
        ) -> script_helper.ScriptRunResult | None:
            try:
                for condition in conditions:
                    if not condition.async_check(variables=variables):
                        return None

                parent_id = None if context is None else context.id
                trigger_context = Context(parent_id=parent_id)
                return await action_script.async_run(variables, trigger_context)
            except vol.Invalid, HomeAssistantError:
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

        def references(
            action_script: script_helper.Script = action_script,
            condition_config: tuple[ConfigType, ...] = tuple(condition_config),
            trigger_config: tuple[ConfigType, ...] = tuple(trigger_config),
        ) -> tuple[set[str], set[str]]:
            """Return what the removed AutomationEntity reported as referenced."""
            entities = set(action_script.referenced_entities)
            devices = set(action_script.referenced_devices)
            for conf in condition_config:
                entities |= condition_helper.async_extract_entities(conf)
                devices |= condition_helper.async_extract_devices(conf)
            for conf in trigger_config:
                entities.update(trigger_helper.async_extract_entities(conf))
                devices.update(trigger_helper.async_extract_devices(conf))
            return entities, devices

        _publish(hass, name, item, STATE_ON, references)

    return True


async def async_setup_script(hass: HomeAssistant, config: ConfigType) -> bool:
    """Expose YAML script definitions as test-only entities and services."""
    raw_scripts = config.get(SCRIPT_DOMAIN, {})
    if not isinstance(raw_scripts, dict):
        return True

    data = hass.data.setdefault(_SCRIPT_DATA, {"scripts": {}, "references": {}})
    scripts = data["scripts"]

    for service_name, item in raw_scripts.items():
        try:
            sequence = cv.SCRIPT_SCHEMA(item.get("sequence", []))
            sequence = await script_helper.async_validate_actions_config(hass, sequence)
        except (vol.Invalid, HomeAssistantError) as err:
            _LOGGER.error(
                "Script %s could not be prepared and has been disabled: %s",
                service_name,
                err,
            )
            continue

        name = item.get("alias", service_name)
        action_script = script_helper.Script(
            hass,
            sequence,
            name,
            SCRIPT_DOMAIN,
        )
        entity_id = _register(hass, SCRIPT_DOMAIN, service_name, service_name, name)
        scripts[entity_id] = action_script
        data["references"][entity_id] = lambda action_script=action_script: (
            action_script.referenced_entities,
            action_script.referenced_devices,
        )
        hass.states.async_set(entity_id, STATE_OFF, {"friendly_name": name})

        async def async_run_script(
            call: ServiceCall,
            *,
            action_script: script_helper.Script = action_script,
        ) -> None:
            await action_script.async_run(dict(call.data), call.context)

        hass.services.async_register(SCRIPT_DOMAIN, service_name, async_run_script)

    if not hass.services.has_service(SCRIPT_DOMAIN, SERVICE_RELOAD):

        async def async_reload(_call: ServiceCall) -> None:
            await _async_reload_scripts(hass)

        hass.services.async_register(SCRIPT_DOMAIN, SERVICE_RELOAD, async_reload)

    if not hass.services.has_service(SCRIPT_DOMAIN, SERVICE_TURN_ON):

        async def async_turn_on(call: ServiceCall) -> None:
            for entity_id in cv.comp_entity_ids(call.data[ATTR_ENTITY_ID]):
                await hass.data[_SCRIPT_DATA]["scripts"][entity_id].async_run(
                    call.data.get("variables"), call.context
                )

        hass.services.async_register(SCRIPT_DOMAIN, SERVICE_TURN_ON, async_turn_on)

    return True


async def _async_reload_scripts(hass: HomeAssistant) -> None:
    """Replace the harness scripts with the ones in the reloaded YAML."""
    config = await conf_util.async_hass_config_yaml(hass)
    data = hass.data[_SCRIPT_DATA]
    for entity_id, action_script in data["scripts"].items():
        await action_script.async_stop()
        hass.services.async_remove(SCRIPT_DOMAIN, split_entity_id(entity_id)[1])
        hass.states.async_remove(entity_id)
    data["scripts"].clear()
    data["references"].clear()
    await async_setup_script(hass, config)
