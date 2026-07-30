# Credential Hygiene — Action Required

## Live credentials are committed to this repository

`.env.local` and `.env.prod` are **tracked by git** and contain working
credentials. They are listed in `.gitignore`, but that has no effect on files
already tracked — git only ignores files it does not know about.

Confirmed present in committed history:

| File | Credential |
|---|---|
| `.env.local` | `npci` MySQL username and password |
| `.env.local`, `.env.prod` | `JWT_SECRET` |
| `.env.local`, `.env.prod` | `INTERNAL_BYPASS_SECRET` |

The remote is `github.com/GitHub-akhilesh/Django_apis_digipay`. Anyone with read
access to the repository — now or from any past clone, fork or CI cache — has
these values. Deleting the files in a new commit does **not** remove them from
history.

`JWT_SECRET` is the signing key for DigiPay session tokens. Whoever holds it can
mint a token for any `cscId` and any role, which the AI platform will verify as
genuine. `INTERNAL_BYPASS_SECRET` grants the internal-client bypass on the legacy
API, skipping user authentication entirely.

## What to do

**1. Rotate the credentials.** This is the only step that actually revokes
exposure; everything else is cleanup.

- `JWT_SECRET` — rotate on the DigiPay gateway and every service that verifies
  its tokens. They must all share the new value or tokens minted by one are
  rejected by another. Existing sessions are invalidated, so schedule it.
- `INTERNAL_BYPASS_SECRET` — rotate on the legacy API and the AI platform together.
- `npci` MySQL password — rotate and update every consumer.

**2. Stop tracking the files** so future edits cannot add more:

```bash
git rm --cached .env.local .env.prod
git commit -m "Stop tracking env files containing credentials"
```

`.gitignore` already lists them, so they stay on disk and are ignored from then
on. Tell the team, since a `git pull` will delete their local copy — provide
`.env.example` / `.env.docker.example` as the templates to copy from.

**3. Decide about history.** Purging the values needs a history rewrite
(`git filter-repo`, or GitHub Support for a fork/cache purge). That rewrites every
commit hash and forces everyone to re-clone, so it is a team decision. **Rotation
in step 1 matters more** — once the values are dead, their presence in history is
an audit finding rather than a live risk.

## Keeping it clean

- Secrets belong in environment variables injected by the platform (Kubernetes
  Secrets, CI secret store), not in files in the repo.
- `.env.docker` is gitignored; copy it from `.env.docker.example` and keep real
  values only there.
- The Kubernetes manifest reads `JWT_SECRET`, `INTERNAL_BYPASS_SECRET` and
  `OPENAI_API_KEY` from `ai-platform-secret`. Replace the placeholders with real
  values via `kubectl create secret`, not by editing the manifest into git.
- The client RSA key at `GATEWAY_CLIENT_KEY_PATH` is gitignored and generated at
  runtime. Keep it that way; it must persist across restarts but must not be
  committed.

## Related

- [ENVIRONMENTS.md](../operations/ENVIRONMENTS.md) — which setting lives where
- [deployment.md](../operations/deployment.md) — pre-deployment checklist
