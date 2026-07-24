# Operations Runbook 01 — Production Deployment Guide

## Overview
This runbook covers step-by-step procedures for deploying DigiPay AI Platform backend services and publishing SDK npm packages (`@digipay/chat-core`, `@digipay/chat-react`).

## Pre-Deployment Checklist
1. All PRs merged into `main` branch.
2. `python scripts/check_bundle_budget.py` returns **PASS** (SDK < 15KB, Widget < 30KB).
3. `python tests/contract/test_sdk_api_contracts.py` returns **PASS**.
4. Playwright multi-browser E2E test matrix passed with 100%.

## Deployment Steps
1. **Tag Version Release**:
   ```bash
   git tag -a v2.0.0-RC1 -m "Release Candidate 1"
   git push origin v2.0.0-RC1
   ```
2. **Automated CI/CD Execution**:
   - GitHub Actions workflow `.github/workflows/release-publish.yml` executes automatically on tag push.
   - Verifies bundle sizes, builds monorepo targets, and publishes to NPM registry.
3. **CDN Invalidation**:
   - Invalidate edge CDN cache for `https://cdn.digipay.com/sdk/digipay-chat-sdk.js` and `digipay-chat-widget.js`.

## Post-Deployment Verification
- Run `python scripts/verify_local.py` against live endpoint.
- Verify Telemetry Dashboard shows active status: `docs/site/telemetry.html`.
