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
     balance reads `DigipayUsers` (refreshed from `transactions`) and the passbook
     needs the sharded `digipay_ledger_<n>` tables; against SQLite every legacy
     answer is structurally valid and empty.
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

## Production server: legacy API on 10.1.76.194

The Docker topology above is how the two services are *packaged*. The legacy
DigiPay API is currently deployed on `10.1.76.194` a different way — bare metal
under systemd, no containers — so deploy it with the procedure in this section.

### Topology as deployed

| Port | Managed by | Runs as | Source |
|---|---|---|---|
| 80 | `digipay-api.service` (systemd) | `root` | `/home/akhilesh/digipay_api` |
| 8000 | detached `uvicorn`, **not** a unit | `akhilesh` | same directory |

Both serve the same code from the same tree; only the process manager differs.
This is what "root level and user level" refers to — one directory, two
listeners. **Restart both**, or `:8000` silently keeps serving the old build.

`nginx` is installed but **inactive**; the application binds `:80` directly.
`/etc/nginx/conf.d/digipay.conf` proxies to a gunicorn socket for the separate
Django app under `/root/new_digipay` and is unrelated to this service.

Two standing hazards:

- **`digipay-fastapi.service` is a duplicate unit that also binds `:80`.** It is
  stopped and disabled. If it is ever re-enabled, both units fight for the port
  and the loser crash-loops (`Errno 98 Address already in use`) — it accumulated
  123,270 restarts this way. Leave it disabled.
- **The `:8000` instance is unmanaged.** It does not survive a reboot, and if its
  master process is killed the worker forks are orphaned and keep the port bound
  while serving whatever code was current when they started. Converting it to a
  systemd unit (on `:8000`, never `:80`) would remove this class of problem.

### Never ship `app/config.py` to this server

The server's `config.py` reads its env files in the order `.env.prod, .env.local,
.env`, so `.env` wins and the app targets **PROD `10.1.74.201`**. The repository
version uses `.env.prod, .env, .env.local`, so `.env.local` wins — and that file
on the server points at **UAT `10.1.74.180`**. Deploying the repository
`config.py` therefore switches production onto the UAT database silently, with
no error and no visible symptom. Exclude it from the package; the deploy check
below asserts `DB_HOST` afterwards to catch the mistake if it ever happens.

For the same reason, do not ship `app/tests/`, and extract additively so the
server's own `app/services/tool_apis.py` (orphaned, not imported by this
codebase) is left alone.

### langgraph is not installed on this server

`app/services/agent_service.py` imports `langgraph` inside a `try/except
ImportError` and falls back to `_run_graph_fallback()`, which walks the same
nodes and routing as `build_agent_graph()`. `AgentState` declares no reducers,
so langgraph merges each node's partial return by overwrite — exactly what the
fallback's `dict.update()` does. The chat endpoint is fully functional without
langgraph; do not "fix" this by installing it on a whim, as langchain pulls in a
pydantic version that the running service does not otherwise need.

### Procedure

Dry-run first. A staging copy catches import errors, schema drift and response
regressions **before** the live tree is touched:

```bash
STAGE=~/.deploy-stage
rm -rf $STAGE && mkdir -p $STAGE && chmod 700 $STAGE
cp -r app $STAGE/ && cp .env* $STAGE/
tar -xzf /tmp/app_deploy.tgz -C $STAGE          # package excludes config.py
cd $STAGE && PYTHONPATH=$STAGE ~/digipay_api/venv/bin/python -c 'import app.main'
rm -rf $STAGE                                    # removes the copied env files
```

Then deploy, keeping a backup you can actually restore from:

```bash
sudo tar -czf ~/backups/app-$(date +%Y%m%d-%H%M%S).tgz app
sudo find app -name __pycache__ -type d -exec rm -rf {} +   # sudo: root-owned
tar -xzf /tmp/app_deploy.tgz -C ~/digipay_api
sudo chown -R akhilesh:akhilesh app
./venv/bin/python -m compileall -q app
sudo systemctl restart digipay-api.service                  # port 80
# port 8000 — kill the old listener, then relaunch detached
setsid nohup ./venv/bin/python -m uvicorn app.main:app \
  --host 0.0.0.0 --port 8000 --workers 2 > logs/uvicorn-8000.log 2>&1 &
```

`__pycache__` is written by the root-owned service, so a plain `rm -rf app` fails
partway as `akhilesh`. Do not chain the restore as `rm -rf app && tar -xzf ...`:
the `rm` exits non-zero, the `&&` swallows the restore, and the tree is left
half-deployed. Use `sudo` and run the two commands unconditionally.

### Verification

```bash
H='-H Content-Type:application/json -H X-Client-Id:LOG_SERVICE
   -H X-Bypass-Secret:<INTERNAL_BYPASS_SECRET>'
for P in 80 8000; do
  curl -s http://127.0.0.1:$P/api/v1/health
  curl -s -X POST http://127.0.0.1:$P/api/v1/wallet_balance $H \
    -d '{"csc_ids":["523816200013","745277760013"]}'
done
```

Expected, identical on both ports:

```
{"status":"OK","msg":"API service is healthy"}
{"523816200013":"191.55","745277760013":"420.29"}
```

Those two CSC IDs are real rows in `DigipayUsers` and are the regression check —
if either amount changes, the balance path has moved and you should roll back.
Do **not** use `500100100014` as a probe: it exists in neither `DigipayUsers` nor
`transactions`, so it correctly returns `Wallet balance not available` (see
`ENVIRONMENTS.md`).

Also confirm the deploy did not move the database target:

```bash
./venv/bin/python -c "from app.config import settings; print(settings.DB_HOST)"
# expect 10.1.74.201 on this server
```

### AI platform on the same host (port 8001)

The chat platform runs on `10.1.76.194` too, but is deliberately **not** part of
the legacy deployment above. It lives in its own tree with its own interpreter,
so nothing it installs can disturb the running legacy service:

| | Legacy API | AI platform |
|---|---|---|
| tree | `/home/akhilesh/digipay_api` | `/home/akhilesh/ai_platform_svc` |
| python | 3.9.19 | **3.11.9** |
| venv | `venv/` | its own `venv/` |
| ports | 80, 8000 | 8001 |

**Python 3.11 is not optional.** `langgraph>=1.0` declares `Requires-Python
>=3.10`, so on the legacy venv's 3.9 pip resolves nothing at all and fails with
`No matching distribution found for langgraph>=1.0.0`. The host already has
`python3.11` alongside 3.9; build the platform venv from that.

The tree contains a copy of `app/` as well, because
`ai_platform/api/openapi_aggregate.py` imports `app.routers.v1` to fold the
legacy endpoints into one Swagger page. Those routers are only introspected on a
throwaway `FastAPI()` to read their schema — they are never mounted and never
execute here, so this copy needs no database credentials.

Give the tree **exactly one** `.env`. The repository layout has
`.env.prod`/`.env`/`.env.local` with `.env.local` winning, which is the same
precedence trap described above. Generate it on the server so `JWT_SECRET` and
`INTERNAL_BYPASS_SECRET` are copied from the legacy service's `.env` rather than
retyped — the two must agree or tokens minted by one are rejected by the other.

#### Outbound access needs the proxy

This host has **no direct internet route**. Both PyPI and the DigiPay gateway
answer only through the corporate proxy:

```
                          direct      via 10.1.77.179:12531
pypi.org                    fail              200
files.pythonhosted.org      fail              200
digipayapi.csccloud.in      fail              200
```

`10.1.55.172:12531` and `10.1.77.59:12531` were both unreachable from here; use
`10.1.77.179:12531`.

Install with `pip --proxy`, and give the running service the proxy through the
environment — the gateway clients build `httpx.AsyncClient` without
`trust_env=False`, so httpx picks these up on its own:

```bash
export HTTPS_PROXY=http://10.1.77.179:12531
export HTTP_PROXY=http://10.1.77.179:12531
export NO_PROXY=127.0.0.1,localhost,10.1.76.194,10.1.74.201,10.1.74.180,.csc.gov.local
```

`NO_PROXY` is load-bearing: the platform calls the legacy API at
`http://127.0.0.1:8000`, and sending that through the proxy would fail.

```bash
SVC=/home/akhilesh/ai_platform_svc
python3.11 -m venv $SVC/venv
$SVC/venv/bin/python -m pip install --proxy http://10.1.77.179:12531 -r $SVC/requirements.txt
cd $SVC && setsid nohup ./venv/bin/python -m uvicorn main:app --app-dir ai_platform \
  --host 0.0.0.0 --port 8001 --workers 2 > logs/uvicorn-8001.log 2>&1 &
```

#### Redis and MongoDB

Both are installed on this host, bound to **loopback only** and enabled at boot.
That binding is deliberate: neither has authentication configured and the host
sits on a routable corporate LAN, so listening on `0.0.0.0` would publish an
unauthenticated datastore to the network. The platform is on the same host and
reaches them at `127.0.0.1`.

Two version constraints, both of which fail in a way that does not point at the
cause:

- **Redis must be 6.x, not the default 5.** Rocky 8's default module stream is
  `redis:5`, but `redis-py` 8.x negotiates RESP3 by default and so opens every
  connection with `HELLO 3`. Redis 5 has no `HELLO` command (added in 6), so the
  client dies with ``unknown command `HELLO` `` and the platform silently falls
  back to its in-process session store — Redis is up, reachable, and completely
  unused. Switch the stream:

  ```bash
  sudo dnf -y module reset redis && sudo dnf -y module enable redis:6
  sudo dnf -y distro-sync redis          # 5.0.3 -> 6.2.22
  ```

  An rpm upgrade leaves `/etc/redis.conf.rpmnew` and may reset `bind`; re-apply
  `bind 127.0.0.1` and restart.

- **MongoDB must be 4.4 on this host — check AVX first.** mongod 5.0 and later
  require the CPU AVX instruction set, and this machine does not have it. The
  7.0 packages install perfectly happily and then refuse to start. Verify before
  choosing a version:

  ```bash
  grep -qw avx /proc/cpuinfo && echo "5.0+ ok" || echo "use 4.4"
  ```

Install both through the proxy (`--setopt=proxy=...`, and a `proxy=` line in the
MongoDB repo file). After restarting the platform, confirm the fallbacks are
genuinely gone rather than assuming — the service starts and answers either way:

```bash
grep -c 'Falling back to local dictionary' logs/uvicorn-8001.log   # expect 0
grep -c 'unknown command .HELLO'           logs/uvicorn-8001.log   # expect 0
curl -s localhost:8001/api/v1/governance/rag/status -H "Authorization: Bearer $TOK"
# expect "mongoReachable": true, with a non-zero document/chunk count
redis-cli -n 2 dbsize        # non-zero after one chat turn
```

#### The LLM key is still unset

There is no `OPENAI_API_KEY` on this host, so planning uses deterministic
keyword routing rather than a model. This degrades by design — chat answers
FAQ/RAG and legacy-backed questions correctly without it. Set the key in
`$SVC/.env` and restart to enable model-driven planning.

#### Verification

```bash
TOK=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/token \
  -H 'Content-Type: application/json' \
  -d '{"username":"deploy","cscId":"523816200013"}' | python3 -c 'import json,sys;print(json.load(sys.stdin)["access_token"])')

curl -s http://127.0.0.1:8001/health                                   # {"status":"UP"}
curl -s http://127.0.0.1:8001/api/v1/governance/services -H "Authorization: Bearer $TOK"
curl -s -X POST http://127.0.0.1:8001/api/v1/chat -H "Authorization: Bearer $TOK" \
  -H 'Content-Type: application/json' \
  -d '{"message":"what is my legacy wallet balance","sessionId":"deploy"}'
```

Expected: the chat reply carries **₹191.55** for `523816200013`, the same figure
`/api/v1/wallet_balance` returns — that is the full path (chat → platform →
legacy API → MySQL) proven in one call. `/docs` must return 200 and list both
APIs: 35 paths, of which 9 are the merged legacy ones.

Gateway-backed answers ("what is my wallet balance", without "legacy") will say
*"Your DigiPay session has expired"* for a locally minted token. That is
correct: the gateway authenticates from a real `access_token` **cookie** and
keeps server-side session state, so only a genuine user token reaches it.

Confirm the read-only boundary survived the deploy:

```bash
curl -s http://127.0.0.1:8001/api/v1/governance/gateway/excluded \
  -H "Authorization: Bearer $TOK"
```

Expected `count: 51` — MONEY_MOVEMENT 16, WRITE 16, AUTH 8, CALLBACK 4,
UNSUPPORTED 4, RECURSION 2, INTERNAL 1 — against 43 allowed (39 gateway + 4
legacy), all read-only.

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
