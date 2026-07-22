# DigiPay AI Platform Operator Guide

This guide documents the day-to-day operations and service level indicators for system administrators.

---

## 1. Key Performance Objectives (SLOs)

* **Availability**: Target >= 99.9% (returns 200/201 status codes).
* **P95 Response Latency**: < 500 ms (for all middleware layers excluding external LLM requests).
* **Planner Success Rate**: > 99%.
* **Cache Hit Ratio**: > 85% for read-only operations.

## 2. Backup & Restore Strategy

### Redis State Backups
* Configure Redis RDB snapshots every 15 minutes.
* Run monthly restoration check drills.

### Administrative Configurations
* Backup `/app/data/admin_config.json` every 24 hours.
