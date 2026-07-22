# Operations Runbook 02 — Rollback Procedure

## Overview
Procedure for executing emergency rollbacks when critical defects or telemetry breaches occur post-deployment.

## Rollback Triggers
- SDK Initialization Failure Rate $> 0.1\%$.
- P1 Security Vulnerability identified.
- Unhandled HTTP 500 error spike $> 1.0\%$.

## Rollback Steps
1. **NPM Package Rollback**:
   ```bash
   npm dist-tag add @digipay/chat-core@2.0.0-beta latest
   npm dist-tag add @digipay/chat-react@2.0.0-beta latest
   ```
2. **CDN Asset Reversion**:
   - Revert CDN alias `digipay-chat-sdk.js` to previous commit artifact.
   - Purge CDN cache instantly.
3. **Backend Service Traffic Shift**:
   - Update API Gateway traffic routing to previous green deployment container image.

## Notification
- Post incident update in `#digipay-platform-alerts` Slack channel.
