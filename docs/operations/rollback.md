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

## Legacy API on 10.1.76.194 (bare metal, no containers)

Step 3 above assumes a container image. That server is deployed from a tarball
under systemd, so roll it back from the backup taken at deploy time
(`docs/operations/deployment.md`, "Production server"):

```bash
cd /home/akhilesh/digipay_api
BACKUP=$(ls -1t /home/akhilesh/backups/app-*.tgz | head -1)
sudo rm -rf app
sudo tar -xzf "$BACKUP" -C /home/akhilesh/digipay_api
sudo chown -R akhilesh:akhilesh app
sudo systemctl restart digipay-api.service digipay-api-8000.service
```

Run the two commands unconditionally — **not** `sudo rm -rf app && sudo tar ...`.
`__pycache__` is root-owned, so the `rm` can exit non-zero, and the `&&` then
skips the restore and leaves the tree half-deployed with the service still up on
its in-memory copy. The failure is invisible until the next restart.

Both listeners serve the same tree, which is why the restart above names both
units: rolling back only `:80` leaves `:8000` running the rolled-back-from build
from memory. Verify **both** ports return the expected balances — see the
verification block in the deployment runbook.

The AI chat platform has its own tree and is rolled back separately:

```bash
sudo systemctl restart digipay-ai-platform.service
```

## Notification
- Post incident update in `#digipay-platform-alerts` Slack channel.
