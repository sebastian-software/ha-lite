"""Typing helpers for Home Assistant tests."""

from collections.abc import Callable, Coroutine
from typing import Any
from unittest.mock import MagicMock

from aiohttp import ClientWebSocketResponse
from aiohttp.test_utils import TestClient


class MockHAClientWebSocket(ClientWebSocketResponse):
    """Protocol for a wrapped ClientWebSocketResponse."""

    client: TestClient
    send_json_auto_id: Callable[[dict[str, Any]], Coroutine[Any, Any, None]]
    remove_device: Callable[[str], Coroutine[Any, Any, Any]]


type ClientSessionGenerator = Callable[..., Coroutine[Any, Any, TestClient]]
type MqttMockPahoClient = MagicMock
"""MagicMock for `paho.mqtt.client.Client`"""
type MqttMockHAClient = MagicMock
"""MagicMock for `homeassistant.components.mqtt.MQTT`."""
type MqttMockHAClientGenerator = Callable[..., Coroutine[Any, Any, MqttMockHAClient]]
"""MagicMock generator for `homeassistant.components.mqtt.MQTT`."""
type WebSocketGenerator = Callable[..., Coroutine[Any, Any, MockHAClientWebSocket]]
