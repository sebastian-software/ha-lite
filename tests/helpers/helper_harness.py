"""Test-only stand-ins for removed helper integrations.

`input_boolean` and `intent_script` are absent from ha-lite; `input_boolean`
is only a compat module that names its domain. Catalog tests still set them up
as tools: an input_boolean as the switch a thermostat drives, an intent_script
as the handler behind a voice webhook. These stand-ins give those tests what
they use, and nothing more.
"""

from typing import Any

from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_NAME,
    SERVICE_TOGGLE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import (
    config_validation as cv,
    intent,
    script as script_helper,
    template,
)
from homeassistant.helpers.restore_state import async_get as async_get_restore_data
from homeassistant.helpers.typing import ConfigType


def async_mock_service(
    hass: HomeAssistant, domain: str, service: str, handler: Any
) -> None:
    """Register a test-owned service without product translations."""
    hass.services.async_register(domain, service, handler)


class _InputBoolean:
    """Toggle entities in the state machine, switched by the usual services."""

    DOMAIN = "input_boolean"

    @staticmethod
    async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
        """Create a state per configured object id and register the services."""
        domain = _InputBoolean.DOMAIN
        for object_id, conf in (config.get(domain) or {}).items():
            conf = conf or {}
            attributes = {}
            if (name := conf.get(CONF_NAME)) is not None:
                attributes["friendly_name"] = name
            entity_id = f"{domain}.{object_id}"
            if (initial := conf.get("initial")) is not None:
                state = STATE_ON if initial else STATE_OFF
            elif (
                stored := async_get_restore_data(hass).last_states.get(entity_id)
            ) is not None:
                state = stored.state.state
            else:
                state = STATE_OFF
            hass.states.async_set(entity_id, state, attributes)

        def _switch(new_state: str | None):
            async def handle(call: ServiceCall) -> None:
                for entity_id in cv.comp_entity_ids(call.data[ATTR_ENTITY_ID]):
                    if (current := hass.states.get(entity_id)) is None:
                        continue
                    target = new_state or (
                        STATE_OFF if current.state == STATE_ON else STATE_ON
                    )
                    hass.states.async_set(
                        entity_id, target, current.attributes, context=call.context
                    )

            return handle

        for service, new_state in (
            (SERVICE_TURN_ON, STATE_ON),
            (SERVICE_TURN_OFF, STATE_OFF),
            (SERVICE_TOGGLE, None),
        ):
            if not hass.services.has_service(domain, service):
                async_mock_service(hass, domain, service, _switch(new_state))
        return True


class _ScriptedIntent(intent.IntentHandler):
    """Answer an intent with rendered speech, after running its action."""

    def __init__(self, hass: HomeAssistant, intent_type: str, conf: dict) -> None:
        """Keep the speech template and the optional action."""
        self.intent_type = intent_type
        self._speech = (conf.get("speech") or {}).get("text")
        self._action = None
        if (action := conf.get("action")) is not None:
            self._action = script_helper.Script(
                hass, cv.SCRIPT_SCHEMA(action), f"Intent {intent_type}", "intent_script"
            )

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        """Run the action with the slot values, then speak."""
        variables: dict[str, Any] = {
            key: value["value"] for key, value in intent_obj.slots.items()
        }
        if self._action is not None:
            await self._action.async_run(variables, intent_obj.context)
        response = intent_obj.create_response()
        if self._speech is not None:
            speech = template.Template(self._speech, intent_obj.hass)
            response.async_set_speech(
                speech.async_render(variables, parse_result=False)
            )
        return response


class _IntentScript:
    """Register one scripted intent handler per configured intent type."""

    DOMAIN = "intent_script"

    @staticmethod
    async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
        """Register the handlers."""
        for intent_type, conf in (config.get(_IntentScript.DOMAIN) or {}).items():
            intent.async_register(hass, _ScriptedIntent(hass, intent_type, conf))
        return True


input_boolean = _InputBoolean
intent_script = _IntentScript

SETUP = {
    input_boolean.DOMAIN: input_boolean.async_setup,
    intent_script.DOMAIN: intent_script.async_setup,
}
