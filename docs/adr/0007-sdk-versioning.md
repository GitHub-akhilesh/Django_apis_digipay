# ADR-0007: Semantic Versioning & Package Registry Policy

- **Status**: Accepted
- **Date**: 2026-07-22
- **Deciders**: DigiPay Platform Architecture Board

## Context
Multi-package monorepo releases (`@digipay/chat-core`, `@digipay/chat-react`, `@digipay/chat-widget`) require predictable semver lifecycle management.

## Decision
Enforce strict Semantic Versioning (`MAJOR.MINOR.PATCH-PRERELEASE`). Release tags (`v2.0.0-beta`, `v2.0.0-RC1`, `v2.0.0-GA`) trigger automated GitHub Actions build, test, and npm registry publishing pipelines.

## Consequences
- **Positive**: Automated release notes, zero manual publishing risk.
- **Negative**: Requires rigid commit tag discipline.
