# ADR-0006: Web Component Shadow DOM Widget Isolation

- **Status**: Accepted
- **Date**: 2026-07-22
- **Deciders**: DigiPay Platform Architecture Board

## Context
Embedding UI components into third-party merchant web pages often suffers from global CSS contamination and style bleeding.

## Decision
Package `<digipay-chat>` as a Web Component encapsulated within a Shadow DOM boundary, isolating all typography, layout, and colors from host CSS pollution.

## Consequences
- **Positive**: 100% style isolation and visual fidelity across any host app.
- **Negative**: Custom styling requires explicit CSS custom properties or theme attributes.
