# Enterprise AI Platform Architecture

This document describes the high-level architecture of the standalone Enterprise AI Support Platform.

## Logical Architecture

The platform sits alongside the existing enterprise microservices ecosystem (Spring Boot microservices, MySQL databases, Redis, Kafka, and telemetry) as a dedicated, low-latency intelligence layer.

```
+-------------------------------------------------------------+
|                       Client Layer                          |
|             (React Web / Flutter Mobile / WhatsApp)          |
+-------------------------------------------------------------+
                               │
                      WebSocket / SSE (JWT)
                               │
                               ▼
+-------------------------------------------------------------+
|                       AI Gateway                            |
|             (FastAPI Service, Auth, Rate Limiter)           |
+-------------------------------------------------------------+
                               │
                               ▼
+-------------------------------------------------------------+
|                     Agentic Orchestration                   |
|                  (LangGraph Workflow Engine)                |
+-------------------------------------------------------------+
       │                       │                       │
       ▼                       ▼                       ▼
+--------------+        +--------------+        +--------------+
|  Memory Hub  |        |  RAG Engine  |        | Tool Router  |
|   (Redis)    |        | (Vector DB)  |        |  (REST APIs) |
+--------------+        +--------------+        +--------------+
                                                       │
                                                       ▼
                                            +------------------+
                                            | Spring Boot APIs |
                                            +------------------+
```

## Architectural Components

1. **AI Gateway (FastAPI)**:
   - Manages connection lifecycle (WebSockets/SSE).
   - Validates client JWT token context during the initial handshake.
   - Enforces rate-limiting windows.
   - Instruments Prometheus metrics and Zipkin trace contexts.

2. **Agentic Orchestrator (LangGraph)**:
   - State-machine workflow coordinator.
   - Routes requests to specialized sub-agents based on intent classification.
   - Executes validation loops to prevent hallucinations and enforce business compliance rules.

3. **Memory Engine (Redis)**:
   - Stores session-level conversation history with a 24-hour expiration window.
   - Archives logs asynchronously to cold storage (e.g., PostgreSQL) via Kafka event buses for compliance audits.

4. **Knowledge Base RAG (Vector Database)**:
   - Matches user questions against internal SOPs, merchant guidelines, NPCI limits, and runbooks.
   - Returns context payloads to supplement LLM prompts.
   - Backed by **MongoDB** (`rag_documents`, `rag_chunks`), using Atlas
     `$vectorSearch` when available and in-process cosine similarity otherwise.
     Falls back to an in-memory index if MongoDB is unreachable, so a knowledge
     store outage degrades answer quality rather than availability.

5. **Tool Router Adapter**:
   - Converts AI function calls into verified HTTP REST calls to the Spring Boot microservices ecosystem.
   - Prevents the LLM from executing raw database queries, ensuring RBAC, input validation, and business logic are owned entirely by the Spring Boot backend.

## Backing systems

The platform reads from three separate systems and re-serves none of their
routes, so integrating it changes no existing URL:

| System | Base URL | Reached via |
|---|---|---|
| DigiPay gateway-service (Spring Boot) | `https://digipayapi.csccloud.in/gateway` (prod) / `https://digipayapiuat.csccloud.in/gateway` (UAT) | `gateway/v2/*` clients |
| Legacy DigiPay API (`app/main.py`) | its own host, paths unchanged (`/api/v1/*`) | `gateway/legacy_v1/client.py` |
| MongoDB | `MONGO_URI` | `rag/mongo_store.py` |

The `/gateway` context path is mandatory — see
[../operations/ENVIRONMENTS.md](../operations/ENVIRONMENTS.md).

## Read-only boundary

The assistant has **read-only** access, enforced in code rather than by
convention. `gateway/v2/safety.py` and `gateway/legacy_v1/client.py` each hold an
explicit allow-list; a request to any other path raises before a socket is
opened. Money movement, record writes, device registration, OTP issuance and
authentication are recorded in a matching exclusion register with the reason, and
both registers are served by `/api/v1/governance/gateway/{allowed,excluded}` so
the deployed reality is inspectable.

Encrypted responses: `GET /v2/ledger/balance` returns the balance encrypted to
the caller's own RSA public key, advertised in the `X-Frontend-Key` header
(`gateway/v2/crypto.py`). That header is not a shared secret.
