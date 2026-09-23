"""Test for the conversation traces."""

from unittest.mock import patch

import pytest

from homeassistant.components import conversation
from homeassistant.components.conversation import DOMAIN, trace
from homeassistant.components.homeassistant.exposed_entities import async_expose_entity
from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.setup import async_setup_component

from tests.common import async_mock_service


@pytest.fixture
async def init_components(hass: HomeAssistant):
    """Initialize relevant components with empty configs."""
    assert await async_setup_component(hass, "homeassistant", {})
    assert await async_setup_component(hass, DOMAIN, {})
    assert await async_setup_component(hass, "intent", {})


async def test_converation_trace(
    hass: HomeAssistant,
    init_components: None,
) -> None:
    """Test tracing a conversation."""
    hass.states.async_set("light.kitchen", "off", {"friendly_name": "kitchen light"})
    async_expose_entity(hass, conversation.DOMAIN, "light.kitchen", True)
    async_mock_service(hass, "light", "turn_on")

    await conversation.async_converse(
        hass, "turn on the kitchen light", None, Context()
    )

    traces = trace.async_get_traces()
    assert traces
    last_trace = traces[-1].as_dict()
    assert last_trace.get("events")
    assert len(last_trace.get("events")) == 2
    trace_event = last_trace["events"][0]
    assert (
        trace_event.get("event_type") == trace.ConversationTraceEventType.ASYNC_PROCESS
    )
    assert trace_event.get("data")
    assert trace_event["data"].get("text") == "turn on the kitchen light"
    assert last_trace.get("result")
    assert (
        last_trace["result"]
        .get("response", {})
        .get("speech", {})
        .get("plain", {})
        .get("speech")
        == "Turned on the light"
    )

    trace_event = last_trace["events"][1]
    assert trace_event.get("event_type") == trace.ConversationTraceEventType.TOOL_CALL
    assert trace_event.get("data") == {
        "intent_name": "HassTurnOn",
        "slots": {"name": "kitchen light"},
    }


async def test_converation_trace_uncaught_error(
    hass: HomeAssistant,
    init_components: None,
) -> None:
    """Test tracing a conversation that raises an uncaught error."""
    with (
        patch(
            "homeassistant.components.conversation.default_agent.DefaultAgent.async_process",
            side_effect=ValueError("Unexpected error"),
        ),
        pytest.raises(ValueError),
    ):
        await conversation.async_converse(
            hass, "turn on the kitchen light", None, Context()
        )

    traces = trace.async_get_traces()
    assert traces
    last_trace = traces[-1].as_dict()
    assert last_trace.get("events")
    assert len(last_trace.get("events")) == 1
    trace_event = last_trace["events"][0]
    assert (
        trace_event.get("event_type") == trace.ConversationTraceEventType.ASYNC_PROCESS
    )
    assert last_trace.get("error") == "Unexpected error"
    assert not last_trace.get("result")


async def test_converation_trace_homeassistant_error(
    hass: HomeAssistant,
    init_components: None,
) -> None:
    """Test tracing a conversation with a HomeAssistant error."""
    with (
        patch(
            "homeassistant.components.conversation.default_agent.DefaultAgent.async_process",
            side_effect=HomeAssistantError("Failed to talk to agent"),
        ),
    ):
        await conversation.async_converse(
            hass, "turn on the kitchen light", None, Context()
        )

    traces = trace.async_get_traces()
    assert traces
    last_trace = traces[-1].as_dict()
    assert last_trace.get("events")
    assert len(last_trace.get("events")) == 1
    trace_event = last_trace["events"][0]
    assert (
        trace_event.get("event_type") == trace.ConversationTraceEventType.ASYNC_PROCESS
    )
    result = last_trace.get("result")
    assert result
    assert result["response"]["speech"]["plain"]["speech"] == "Failed to talk to agent"
