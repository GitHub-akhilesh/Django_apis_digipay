# Operations Runbook 01 — Production Deployment Guide

## Overview
This runbook covers step-by-step procedures for deploying DigiPay AI Platform backend services and publishing SDK npm packages (`@digipay/chat-core`, `@digipay/chat-react`).

Environment addresses, the mandatory `/gateway` context path, and the settings
each service needs are documented in **[ENVIRONMENTS.md](ENVIRONMENTS.md)**. Read
that first — a wrong `API_GATEWAY_URL` is the most common cause of a deployment
where chat starts but every data lookup fails.

## Pre-Deployment Checklist
1. All PRs merged into `main` branch.
2. `python -m pytest ai_platform/tests/ -q` returns **PASS**.
3. `python scripts/check_bundle_budget.py` returns **PASS** (SDK < 15KB, Widget < 30KB).
4. `python tests/contract/test_sdk_api_contracts.py` returns **PASS**.
5. Playwright multi-browser E2E test matrix passed with 100%.
6. Backend configuration confirmed:
   - `API_GATEWAY_URL` ends in **`/gateway`** and matches the target environment
     (`https://digipayapi.csccloud.in/gateway` for production).
   - `JWT_SECRET` and `INTERNAL_BYPASS_SECRET` are **identical** across the AI
     platform and the legacy DigiPay API service.
   - `AI_PLATFORM` is present in the legacy service's `INTERNAL_CLIENTS`.
   - `GATEWAY_CLIENT_KEY_PATH` is on a **persistent volume** — a key regenerated
     between a request and its response makes encrypted ledger balances
     undecryptable.
   - `OPENAI_API_KEY` is set. Empty means chat falls back to offline keyword
     routing and lexical RAG embeddings, which is a local-testing mode only.
   - `DATABASE_URL` points at the **`npci` MySQL**, not SQLite. The legacy wallet
     balance sums the `transactions` table and the passbook needs the sharded
     `digipay_ledger_<n>` tables; against SQLite every legacy answer is
     structurally valid and empty.
   - `CORS_ALLOW_ORIGINS` lists the browser origins that will call this service.
   - `JWT_ROLE_MAP` reviewed — confirm whether your DigiPay `ADMIN` is a CSC owner
     (default, maps to `ROLE_MERCHANT`) or a platform administrator. Getting this
     wrong in the permissive direction is a privilege escalation.
   - `AI_PLATFORM` present in the legacy service's `INTERNAL_CLIENTS`, or set
     `LEGACY_INTERNAL_CLIENT_ID` to a client id that server already accepts.

## Backend services

Two services deploy separately and keep their existing URLs, so no frontend
change is required:

| Service | Command | Port |
|---|---|---|
| Legacy DigiPay API | `uvicorn app.main:app --host 0.0.0.0 --port 8000` | 8000 |
| AI Platform | `uvicorn main:app --app-dir ai_platform --host 0.0.0.0 --port 8001` | 8001 |

Both run from the **same image**; only the command differs. The build context
must be the repository root — `requirements.txt` lives there, and the AI platform
imports `app.routers.v1` to document the legacy API in its own Swagger UI.

```bash
cp .env.docker.example .env.docker      # then set the secrets
docker compose --env-file .env.docker up -d --build
docker compose --env-file .env.docker ps      # all four services healthy
```

`--env-file` is deliberate: both applications also read a root `.env`, so putting
Compose variables there would silently alter a non-Docker run.

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
- Confirm the gateway is reachable on the right context path:
  ```bash
  curl -s https://digipayapi.csccloud.in/gateway/v2/user/publickey | head -c 80
  # expect: {"status":"OK","msg":"Backend public key fetched successfully"...
  curl -so /dev/null -w '%{http_code}\n' \
    https://digipayapi.csccloud.in/gateway/actuator/health      # expect 200
  ```
- Confirm the AI platform resolved the intended backing services:
  ```bash
  curl -s -H "Authorization: Bearer $TOKEN" \
    https://<ai-platform-host>/api/v1/governance/services
  ```
  Check the reported `baseUrl` for `gateway-service` and `legacy-digipay-api`.
- Confirm both APIs appear in one Swagger page at `/docs` on the AI platform, and
  that the legacy paths carry a `servers` override pointing at a host a browser
  can reach (`LEGACY_API_PUBLIC_URL`).
- Confirm the read-only boundary is intact:
  ```bash
  curl -s -H "Authorization: Bearer $TOKEN" \
    https://<ai-platform-host>/api/v1/governance/gateway/excluded
  ```
  Every money-movement, write and authentication endpoint must be listed.
