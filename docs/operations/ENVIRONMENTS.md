# Operations Runbook — Environments & Backend Configuration

Canonical reference for the addresses each service talks to. If a chat data
lookup returns "I couldn't fetch that", start here.

## Services in the platform

Three separate systems. Each keeps its own URLs; none of them proxies another.

| Service | Code | Local port | Role |
|---|---|---|---|
| **DigiPay gateway-service** | `DigiPay/digipay_setup/gateway-service` (Spring Boot) | 9091 | Source of truth for `/v2/*` and `/v1/upi/*` |
| **Legacy DigiPay API** | `app/main.py` (FastAPI) | 8000 | `/api/v1/txn-logs`, `/passbook`, `/wallet_balance`, `/daywise_report` |
| **AI Platform** | `ai_platform/main.py` (FastAPI) | 8001 | `/api/v1/chat`, `/api/v1/governance/*` |

The AI platform **reads** from the other two over HTTP. It never re-serves their
routes, so no frontend URL changes when it is deployed.

## Gateway base URLs

One host per environment, shared by the React frontend and this platform.

| Environment | Host |
|---|---|
| Production | `https://digipayapi.csccloud.in` |
| UAT / local | `https://digipayapiuat.csccloud.in` |

Both are **HTTPS only** — port 80 is closed.

```properties
# React (digipay-react-app/.env)
VITE_API_BASE_URL=https://digipayapiuat.csccloud.in

# AI platform (.env.local)
API_GATEWAY_URL=https://digipayapiuat.csccloud.in
API_GATEWAY_CONTEXT_PATH=/gateway
```

### The `/gateway` context path

`gateway-service/configs/app.properties` sets:

```properties
server.port=9091
server.servlet.context-path=/gateway
```

Every controller is mounted beneath it, so the absolute URL is always
`https://<host>/gateway/v2/...`. The two codebases split that URL differently —
both are correct, and both resolve to the same place:

| | Base | Path | Absolute URL |
|---|---|---|---|
| React | `VITE_API_BASE_URL` = bare host | `/gateway/v2/user/publickey`<br>(`src/constants/apiUrls.js`) | `https://host/gateway/v2/user/publickey` |
| AI platform | `API_GATEWAY_URL` + context path | `/v2/user/publickey`<br>(matches the Java `@RequestMapping`) | `https://host/gateway/v2/user/publickey` |

React carries the prefix in ~50 path constants; this platform keeps it in the
base so tool paths mirror the controller annotations verbatim.

**`API_GATEWAY_URL` accepts either spelling.** `gateway_base_url` normalises it,
so the bare host the team shares can be pasted in directly:

```
https://digipayapiuat.csccloud.in          -> https://digipayapiuat.csccloud.in/gateway
https://digipayapiuat.csccloud.in/gateway  -> https://digipayapiuat.csccloud.in/gateway
```

This matters because both failure modes return a Tomcat **HTML** 404 rather than
a JSON error, which reads like "the endpoint does not exist" rather than a
misconfiguration:

```bash
curl https://digipayapiuat.csccloud.in/v2/user/publickey                  # 404 HTML (missing)
curl https://digipayapiuat.csccloud.in/gateway/gateway/v2/user/publickey  # 404 HTML (doubled)
curl https://digipayapiuat.csccloud.in/gateway/v2/user/publickey          # 200 JSON
```

Set `API_GATEWAY_CONTEXT_PATH=""` only if a reverse proxy already strips the
prefix before the request reaches the gateway.

### Health probing

`/health` on the gateway sits behind Spring Security and answers **401**, which
makes a healthy gateway look unreachable. Use the actuator endpoint:

```
API_GATEWAY_HEALTH_PATH=/actuator/health
```

| Path | Status |
|---|---|
| `/gateway/health` | 401 |
| `/gateway/actuator/health` | 200 |

### Authentication

The gateway requires a real end-user **JWT**; the internal-client bypass headers
used for the legacy API are not accepted. Unauthenticated calls return a plain
error object, *not* the `CommonResponseBO` envelope:

```json
{"path":"/gateway/v2/services/master-list","error":"UNAUTHORIZED",
 "message":"Full authentication is required to access this resource","status":401}
```

`GET /v2/user/publickey` is the one route readable without a token, which is why
it is useful as a connectivity check.

## Where each setting lives

| File | Purpose |
|---|---|
| `.env.local` | UAT gateway. Used for local development. |
| `.env.prod` | Production gateway. |
| `.env.docker` | Docker Compose variables only — copy from `.env.docker.example`. |
| `docker-compose.yml` | Defaults to **UAT** so a local stack never hits production by accident. |
| `ai_platform/deploy/kubernetes/production_manifests.yaml` | ConfigMap with the production gateway. |
| `../../DigiPayReact/digipay-react-app/.env` | React `VITE_API_BASE_URL` — the same host, separate repository. |

`GET /api/v1/governance/services` reports both the raw `configuredUrl` and the
resolved `baseUrl`, so you can see exactly what a running instance will call.

### Env-file precedence

Both services load, in increasing priority: `.env.prod` → `.env` → `.env.local`,
resolved as **absolute paths from the repository root**. Real environment
variables override all of them, which is how the containers are configured.

Do not put Compose variables in a root `.env`: both applications read it through
pydantic-settings, so it would silently change a local non-Docker run. That is
why Compose is invoked with `--env-file .env.docker`.

## Legacy DigiPay API

Deployed at **`http://10.1.76.194`** (port 80 — no explicit port). Verified
serving `/api/v1/health` and an `/openapi.json` titled *"DigiPay API Gateway &
Ledger Services"*. React exposes the same host as `VITE_OLD_URL`.
`prod_reference_10_1_76_194/` in this repo is a snapshot of that deployment.

> **Prerequisite:** that server's `INTERNAL_CLIENTS` is
> `WALLET_SERVICE,PASSBOOK_SERVICE,LOG_SERVICE` — it does **not** include
> `AI_PLATFORM`. Until it does, the assistant's read-only calls to
> `/api/v1/txn-logs`, `/passbook` and `/wallet_balance` return **401**. Add
> `AI_PLATFORM` to that list and restart the service, and make sure its
> `INTERNAL_BYPASS_SECRET` matches the AI platform's.

| Setting | Meaning |
|---|---|
| `LEGACY_API_URL` | Server-to-server address the AI platform calls. `http://legacy-api:8000` under Compose; `http://10.1.76.194` to read the deployed instance. |
| `LEGACY_API_PUBLIC_URL` | Address advertised in the merged Swagger schema. Must be reachable from a **browser**, so it cannot be the private container hostname, or "Try it out" fails to resolve the host. Falls back to `LEGACY_API_URL`. |
| `LEGACY_INTERNAL_CLIENT_ID` | Defaults to `AI_PLATFORM`. Must appear in the legacy service's `INTERNAL_CLIENTS`, or its read-only calls get 401. |
| `INTERNAL_BYPASS_SECRET` | Must be **identical** on both services. |
| `JWT_SECRET` | Must be **identical** on both services, or a token minted by one is rejected by the other. |

Database note: `/passbook` and `/txn-logs` query sharded `digipay_ledger_<n>`
tables that exist only in MySQL. Against SQLite they return an empty page, not an
error — the repository layer catches DB failures and returns
`total_records = 0, records = []` with HTTP 200
(`app/repositories/transaction_repo.py`). "No records" and "database down" are
therefore indistinguishable to any caller, including chat.

## Encrypted gateway responses

`GET /v2/ledger/balance` returns the balance encrypted to the caller's own RSA
public key, sent in the `X-Frontend-Key` header. It is **not** a shared secret —
see `ai_platform/gateway/v2/crypto.py`.

| Setting | Meaning |
|---|---|
| `GATEWAY_CLIENT_KEY_PATH` | The platform's own RSA private key. Generated on first start. |
| `GATEWAY_VERIFY_RESPONSE_SIGNATURE` | Verifies the backend's `SHA256withRSA` signature, using the key from `GET /v2/user/publickey`. |

**This key must persist across restarts.** If it changes between the request and
the response, the balance cannot be decrypted. Mount a volume over
`GATEWAY_CLIENT_KEY_PATH` (Compose and the k8s ConfigMap both do).

## Verifying a deployment

```bash
# 1. Gateway reachable and on the right context path
curl -s https://digipayapiuat.csccloud.in/gateway/v2/user/publickey | head -c 120
# expect: {"status":"OK","msg":"Backend public key fetched successfully",...

# 2. Gateway health
curl -so /dev/null -w '%{http_code}\n' \
  https://digipayapiuat.csccloud.in/gateway/actuator/health   # expect 200

# 3. What the AI platform believes it is pointed at
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8001/api/v1/governance/services

# 4. Readiness of every dependency
curl -s http://localhost:8001/ready
```

`/api/v1/governance/services` reports the resolved base URL of each backing
system and how many tools read from it — the fastest way to confirm an
environment is wired to the hosts you intended.

## Gateway behaviours that are not obvious

Each of these produced a bug that looked like a platform fault. Verified against
the live UAT and production gateways.

### `resData` is often base64-encoded JSON

`/v2/device/list`, `/v2/ledger/passbook` and `/v2/txn/logs` return `resData` as
base64 JSON, not an object. The web app decodes it with `decodeParams`
(`atob` + `JSON.parse`); `gateway/v2/base.py::_decode_res_data` does the same.

Without decoding, the raw base64 reaches the user:

```
eyJkZXZpY2VzIjpbXSwiY3NjSWQiOiI1MDAxMDAxMDAwMTQifQ==
```

A bare base64 **key** (`/v2/user/publickey`) is left alone — decoding would
corrupt it.

### `/v2/txn/logs` is per-service, and there is no `ALL`

`type` must be a `com.digipay.common.enums.Category` value —
`AEPS_CASH_WITHDRAWAL`, `AEPS_CASH_DEPOSIT`, `AEPS_MINI_STATEMENT`,
`AEPS_BALANCE_ENQUIRY`, `PAYOUT`, `DSP_TOPUP`, `MATM_ISERVEU`, `MATM_EUREKA`,
`VATM_WITHDRAWAL`, `UPI_CASH_WITHDRAWAL`.

An invented value (including `ALL`) is answered with **HTTP 200 and a non-OK
envelope carrying an empty `msg`** — no diagnostic at all. That is why the
assistant routes generic "transaction history" to the ledger **passbook**, which
is genuinely cross-service, and uses `/v2/txn/logs` only when a service is named.

### `GET /v2/ledger/balance` returns the latest ledger row too

The amount is **`walletBalance`**, not `balance`. The response also carries the
most recent entry: `txnAmount`, `txnType`, `txnDate`, `remarks`, `rrn`,
`vleComm`, `vleTds`, `gst`, `walletDeduction`, `walletAc`, `customer`,
`category`, `cscTxn`, `merchantTxn`, `sno`, `creationDate`, `clientId`,
`deviceType`, `interCharge`.

The passbook returns rows in this same shape.

### Session tokens arrive in a cookie, and use different claim names

A DigiPay session token looks like:

```json
{ "sub": "500100100014", "ownerId": "500100100014",
  "operatorIds": "500100100014,500100100022,500100100107",
  "roles": ["VLE", "ADMIN"], "txnId": "CZU..." }
```

It is signed with the shared `JWT_SECRET`, so it verifies — but note:

| | |
|---|---|
| Transport | the `access_token` **cookie**, not just an Authorization header |
| CSC ID | `ownerId` / `sub`; there is **no** `cscId` or `merchantId` claim |
| Roles | bare `VLE` / `ADMIN`, translated by `JWT_ROLE_MAP` |

**`ADMIN` is deliberately mapped to `ROLE_MERCHANT`, not `ROLE_ADMIN`.** In a
token carrying `ownerId` and `operatorIds`, `ADMIN` means the owner of a CSC
relative to its operators — not a platform administrator. Mapping it to
`ROLE_ADMIN` would grant every CSC owner the platform-wide admin reports and
exempt them from tenant isolation. Change it only if your `ADMIN` really is a
platform role:

```
JWT_ROLE_MAP=VLE=ROLE_MERCHANT,ADMIN=ROLE_ADMIN,OPERATOR=ROLE_USER,SUPPORT=ROLE_SUPPORT
```

The caller's token is forwarded to the gateway, which rejects internal bypass
headers and requires a real end-user JWT.

### CORS must be the outermost middleware

A browser preflight is an `OPTIONS` request with **no** Authorization header. If
the JWT middleware sees it first, it answers 401 without any
`Access-Control-Allow-*` headers, and the browser reports an opaque "CORS error".

`CORSMiddleware` is therefore registered **last** in `main.py` (Starlette
prepends, so last = outermost), and the JWT middleware short-circuits `OPTIONS`
as defence in depth. Allowed origins come from `CORS_ALLOW_ORIGINS`.

## Legacy wallet balance

`POST /api/v1/wallet_balance` is ported from
`CSC_Connect_Digipay/mainapp/digipay_utils.py::cal_wallet_balance`. It is a
**refresh-then-read against `DigipayUsers`**, not a read of `transactions`:

```sql
-- 1. refresh the cached column from the ledger. The inner join means only
--    CSC IDs that actually have transaction rows are touched.
UPDATE DigipayUsers du
JOIN (SELECT user_id, COALESCE(SUM(amount), 0) AS total
        FROM transactions
       WHERE status IN ('SUCCESS','INITIATED') AND user_id IN (...)
       GROUP BY user_id) t ON du.user_id = t.user_id
   SET du.wallet_balance = t.total, du.balance_update_at = ?;

-- 2. the returned value comes from here, not from the sum above
SELECT user_id, wallet_balance FROM DigipayUsers WHERE user_id IN (...);
```

Response shape is unchanged: `{"523816200013": "191.55"}`.

Getting the order right matters, and it is easy to get wrong:

* **The answer is read from `DigipayUsers`.** So `"Wallet balance not available"`
  means *no balance on record* — the CSC ID is absent from `DigipayUsers`, or its
  `wallet_balance` is NULL. A VLE who is on file with a balance of zero and
  simply has no transactions still gets `"0.00"`, because that zero is what the
  table holds. Computing the answer from the sum instead collapses those two
  cases and turns a legitimate `"0.00"` into the sentinel.
* A SQL failure also yields the sentinel, never `"0.00"` — a database error is
  not a balance of zero.
* Step 1's inner join is load-bearing. Refreshing every requested ID instead
  would write `0` over the stored balance of a real user who happens to have no
  `SUCCESS`/`INITIATED` rows.
* This nominally read-only endpoint therefore performs a cache write. It is
  best-effort and cannot fail the read; pass `write_back=False` to skip step 1
  and read the stored value as-is.

Probe with a CSC ID that exists. On PROD (`10.1.74.201`),
`523816200013` → `"191.55"` and `745277760013` → `"420.29"`, while
`500100100014` is in neither `DigipayUsers` nor `transactions` and correctly
returns the sentinel — it is not a valid smoke-test ID.

Note also that PROD has **no `wallets` table**, so the ORM `Wallet` lookup in
`WalletSnapshotService` always fails there and the transactions/`DigipayUsers`
path is the only one that answers. That lookup swallows its error, so it must
roll the session back — otherwise the aborted statement poisons the session and
every later query in the same request fails too, and the fallback never runs.

**This needs MySQL.** The bundled `legacy-api` container runs against an empty
SQLite file, so every legacy answer is structurally correct and empty — a Rs 0.00
balance for an account that actually holds Rs 801,141.48. The passbook and
txn-log queries additionally need the sharded `digipay_ledger_<n>` tables that
only exist in MySQL. Set `DATABASE_URL` to the `npci` MySQL for real data.

## Chat SDK and widget

`sdk/digipay-chat-sdk.js` targets either backend, selected by `api-mode`:

| | `legacy` (default) | `ai-platform` |
|---|---|---|
| auth | `POST /api/v1/auth/token` | the caller's DigiPay JWT |
| chat | `POST /api/v1/agent/chat` | `POST /api/v1/chat` |
| response | flat | `{data: {...}}` envelope |

The widget reads the JWT from `localStorage["authToken"]` and sends
`credentials: 'include'` so the `access_token` cookie travels cross-origin.

Voice uses the browser's Web Speech APIs — no audio leaves the device — across 13
languages, remembered per browser. Speech recognition requires a **secure
context**: `https` or `http://localhost`, not a plain `http://` LAN address.

Copy both files into any host app's static directory after changing them:

```bash
cp sdk/digipay-chat-*.js ../DigiPayReact/digipay-react-app/public/js/
```

## Related runbooks

- `deployment.md` — release and deployment procedure
- `rollback.md` — rollback procedure
- `../architecture/AI_PLATFORM_ARCHITECTURE.md` — component architecture
