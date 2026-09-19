# ADR 0009 — MCP is a core headless control surface

## Status

Accepted.

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

After frontend/Lovelace are physically removed, ha-lite must keep an explicit headless MCP contract test proving a representative MCP round-trip with those packages absent.

Treat `homeassistant-ai/ha-mcp` as an external compatibility canary. A future CI job may install its custom component and exercise its embedded server with UI-only options (especially `enable_sidebar_panel`) disabled. Dashboard/Lovelace-specific tools are outside the compatibility guarantee.

## Consequences

The earlier broad plan to delete Assist/Conversation as product intelligence is narrowed: voice-oriented presentation features may still be removed, but the Conversation/LLM substrate required by MCP remains until a replacement machine-control API exists.

Future deletion waves must distinguish between:

- intelligence/presentation features that can be removed; and
- generic machine-control primitives consumed by MCP that are now protected.

An upstream change that makes `mcp_server` depend on frontend/Lovelace is an architectural regression for ha-lite and must be investigated rather than silently accommodated.
