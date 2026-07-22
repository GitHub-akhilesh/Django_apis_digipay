# DigiPay AI Platform Disaster Recovery Plan

This guide outlines high-availability multi-region cluster recovery steps and disaster restoration paths.

---

## 1. High Availability Architecture

The platform uses a stateless design to handle single-node failures:
* Deploy at least 2 replicas in separate availability zones.
* Redis is configured in cluster replication mode with automated sentinel failover.

## 2. LLM Provider Outage Failover

In case of cloud provider outages:
1. The platform automatically catches provider failures.
2. It transitions query processing to secondary options in the fallback sequence list (e.g. `openai` -> `gemini` -> `ollama`).
3. Admin portal settings allow manual configuration changes at runtime.
