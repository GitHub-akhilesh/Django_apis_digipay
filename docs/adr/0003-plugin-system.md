# ADR-0003: Plugin & Middleware Architecture

- **Status**: Accepted
- **Date**: 2026-07-22
- **Deciders**: DigiPay Platform Architecture Board

## Context
Different consuming applications require specialized behaviors (e.g. analytics tracking, voice input, markdown formatting, attachment uploading) without bloating core bundle size.

## Decision
Implement a modular plugin architecture (`IChatPlugin`) and lifecycle hooks (`onMessageSent`, `onResponseReceived`, `onError`, `onStateChange`). Core bundle remains lightweight (< 5KB), while plugins are loaded on-demand.

## Consequences
- **Positive**: Core bundle stays minimal, extensibility is decoupled.
- **Negative**: Plugin authors must adhere to lifecycle contracts.
