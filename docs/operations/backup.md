# Operations Runbook 07 — Backup & Recovery

## Backup Strategy
1. **Redis Memory Cluster**: Daily RDB snapshots taken at 00:00 UTC and replicated to secondary cloud storage.
2. **Conversation History Logs**: Archived asynchronously to immutable S3 audit logs.

## Disaster Recovery Procedure
- In event of primary database cluster loss, trigger memory storage fallback automatically while restoring Redis RDB snapshot.
- RTO (Recovery Time Objective): **< 5 minutes**.
- RPO (Recovery Point Objective): **< 1 minute**.
