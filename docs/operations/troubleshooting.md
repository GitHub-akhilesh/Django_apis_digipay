# Operations Runbook 05 — Developer & SDK Troubleshooting Guide

## Common Issues & Diagnostics

### 1. `DigiPayChatWidget` fails to render
- **Symptom**: Blank element container or missing launcher button.
- **Fix**: Verify `csc-id` prop is provided. Ensure script tags or React imports match version `@digipay/chat-react@2.0.0-RC1`.

### 2. CORS or WebSocket Connection Error
- **Symptom**: Browser console logs `WebSocket connection to ws://... failed`.
- **Fix**: The SDK automatically falls back to HTTP Long-Polling. Verify network firewall permits outbound HTTPS/WSS to `api.digipay.com`.

### 3. JWT Token Expiration 401
- **Symptom**: Chat message fails after extended idle period.
- **Fix**: The auth interceptor automatically calls `/api/v1/auth/refresh`. Ensure merchant application provides valid refresh token callback.
