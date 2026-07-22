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

5. **Tool Router Adapter**:
   - Converts AI function calls into verified HTTP REST calls to the Spring Boot microservices ecosystem.
   - Prevents the LLM from executing raw database queries, ensuring RBAC, input validation, and business logic are owned entirely by the Spring Boot backend.
