# ADR 0009: MCP is a core headless control surface

- Status: Accepted

## Context

ha-lite removes Home Assistant product/presentation layers while preserving a useful device and integration runtime.

Model Context Protocol (MCP) is a machine-facing control surface rather than a browser presentation feature. Home Assistant Core already ships an official `mcp_server` integration whose hard dependencies are `http` and `conversation`. The upstream MCP test suite exercises real protocol behavior over authenticated SSE and streamable HTTP, including tool enumeration and tool invocation.

A widely used external implementation, `homeassistant-ai/ha-mcp`, also provides an embedded Home Assistant custom component. Its hard Home Assistant dependency is `webhook`; frontend and Lovelace are after-dependencies. Some optional functionality, notably its sidebar/settings panel and dashboard-oriented tools, is presentation-specific and is not part of ha-lite's compatibility promise.

## Decision

Treat agent-driven control as a first-class ha-lite capability.

Retain:

- the official `mcp_server` integration;
- `conversation`, intent and LLM primitives required by that server;
- HTTP/auth/WebSocket/webhook/runtime infrastructure required for machine-facing control;
- enough generic service, state, registry and config-entry machinery for MCP tools to act on retained integrations.

Do not retain frontend or Lovelace merely to satisfy MCP.

The official `tests/components/mcp_server` suite is part of the retained CI contract. It must continue to exercise the real protocol rather than only import/setup behavior.

After frontend/Lovelace are physically removed, ha-lite must keep an explicit headless MCP contract test proving a representative MCP round-trip with those packages absent. `tests/ha_lite/test_mcp_headless.py` is that test. It asserts the removed products cannot be imported, drives initialize, tool listing and a device-affecting tool call over streamable HTTP, and fails if serving that session loads any component outside the retained closure.

Treat `homeassistant-ai/ha-mcp` as an external compatibility canary. A future CI job may install its custom component and exercise its embedded server with UI-only options (especially `enable_sidebar_panel`) disabled. Dashboard/Lovelace-specific tools are outside the compatibility guarantee.

## Consequences

The earlier broad plan to delete Assist/Conversation as product intelligence is narrowed: voice-oriented presentation features may still be removed, but the Conversation/LLM substrate required by MCP remains until a replacement machine-control API exists.

That split has been made. The runtime closure of `mcp_server` and `conversation` contains no voice component: `assist_pipeline`, `assist_satellite`, `stt`, `tts` and `wake_word` were all outside it and have been removed (#23). `ai_task` went with them. `media_source` went too and has come back: it is not voice but the layer that browses and resolves media for camera, image and media player entities. It is an LLM product surface that no retained integration provides, and bootstrap set it up by default only because every entity platform is a default. Agents reach ha-lite through MCP, not through an AI entity inside it.

Future deletion waves must distinguish between:

- intelligence/presentation features that can be removed; and
- generic machine-control primitives consumed by MCP that are now protected.

An upstream change that makes `mcp_server` depend on frontend/Lovelace is an architectural regression for ha-lite and must be investigated rather than silently accommodated.
