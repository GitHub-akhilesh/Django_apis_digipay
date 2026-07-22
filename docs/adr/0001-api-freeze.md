# ADR-0001: API Contract Freeze & Stability Policy

- **Status**: Accepted (v2.0.0-beta / RC1)
- **Date**: 2026-07-22
- **Deciders**: DigiPay Platform Architecture Board

## Context
As the AI platform transitioned into SDK ecosystems and multi-app embed scenarios (Merchant Portal, Admin Portal), unannounced API schema changes posed severe risks of breaking client applications.

## Decision
Freeze all external HTTP, WebSocket, and SDK contract APIs at version `v2.0.0-beta`. No non-backwards-compatible schema changes are permitted without major version increments (`v3.0.0`).

## Alternatives Considered
- *Dynamic Schema Mutation*: Allow schema field additions dynamically. Rejected due to SDK contract fragility.
- *Strict Version Parameter Header*: Require version query params. Rejected in favor of explicit semver endpoints.

## Consequences
- **Positive**: Complete client predictability, automated contract test validation in CI/CD.
- **Negative**: Feature additions must be strictly additive or opt-in via extensions.
