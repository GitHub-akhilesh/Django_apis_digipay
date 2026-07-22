# ADR-0004: Dual-Engine Storage Abstraction (Redis + Memory Fallback)

- **Status**: Accepted
- **Date**: 2026-07-22
- **Deciders**: DigiPay Platform Architecture Board

## Context
High availability requirements mandate zero conversation data loss or server outage crashes if primary Redis memory clusters fail.

## Decision
Implement dual-engine storage abstraction: Redis cluster primary storage with automatic, transparent circuit-breaker fallback to in-memory process storage.

## Consequences
- **Positive**: 99.99% uptime guarantee during cache infrastructure degradation.
- **Negative**: In-memory fallback is node-local until Redis reconnects.
