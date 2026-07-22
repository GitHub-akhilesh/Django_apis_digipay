# Operations Runbook 04 — Incident Response Playbook

## Severity Classifications
- **SEV-1 (Critical)**: Widget fails to load across Merchant Portal; production chat completely unavailable. Response SLA: **15 minutes**.
- **SEV-2 (High)**: High streaming latency ($> 5\text{s}$) or primary LLM outage causing fallback provider switching. Response SLA: **1 hour**.
- **SEV-3 (Medium)**: Minor UI alignment glitch or theme rendering anomaly in specific browser. Response SLA: **24 hours**.

## Incident Response Steps
1. **Declare Incident**: Page On-Call engineer via PagerDuty.
2. **Mitigate**: If SEV-1, trigger CDN rollback or activate memory storage fallback.
3. **Communicate**: Update status page `status.digipay.com`.
4. **Post-Mortem**: Document root cause, timeline, and corrective actions within 48 hours.
