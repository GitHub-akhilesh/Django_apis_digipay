# ADR-0005: JWT Authentication Interceptor & Auto-Refresh

- **Status**: Accepted
- **Date**: 2026-07-22
- **Deciders**: DigiPay Platform Architecture Board

## Context
Long-running enterprise user sessions experience JWT token expiration while users interact with the chat widget.

## Decision
Incorporate automatic 401 interceptors in `@digipay/chat-core` that silently call token refresh endpoints (`/api/v1/auth/refresh`) and retry pending requests seamlessly without user disconnection.

## Consequences
- **Positive**: Zero mid-conversation authentication drops for merchants.
- **Negative**: Client auth providers must supply a valid refresh callback.
