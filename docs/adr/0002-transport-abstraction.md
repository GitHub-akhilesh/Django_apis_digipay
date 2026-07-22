# ADR-0002: Transport Layer Abstraction (HTTP / WS / SSE)

- **Status**: Accepted
- **Date**: 2026-07-22
- **Deciders**: DigiPay Platform Architecture Board

## Context
Clients operate in diverse network environments where WebSockets may be blocked by enterprise firewalls or proxies.

## Decision
Abstract client communications behind a unified `ITransport` interface supporting automatic fallback across WebSockets, Server-Sent Events (SSE), and HTTP Long-Polling.

## Consequences
- **Positive**: 100% network connectivity guarantee across strict enterprise proxies.
- **Negative**: Slight overhead in managing connection state handshakes.
