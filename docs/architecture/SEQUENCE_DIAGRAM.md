# Request Lifecycle Sequence Diagram

This document traces the request-response sequence of a user query seeking transaction details.

```mermaid
sequence_diagram
autonumber

actor User as Client (React/Widget)
participant GW as AI Gateway (FastAPI)
participant Redis as Memory (Redis)
participant Graph as Orchestrator (LangGraph)
participant Tools as Tool Router
participant SB as Spring Boot Backend
participant Vector as Knowledge RAG (Vector DB)

User->>GW: WebSocket Handshake Request (headers: JWT)
activate GW
GW->>GW: Decodes & Validates JWT Claims (extracts cscId)
GW-->>User: Handshake Acknowledged (WS connection open)
deactivate GW

User->>GW: Message: "Where is my money for CZUCW123?"
activate GW
GW->>Redis: Get Session History (sessionId)
Redis-->>GW: Message History List
GW->>Graph: Execute Workflow (message, cscId, history)
activate Graph

Graph->>Graph: Node 1: Intent Routing (Classifies intent as 'Refund')
Graph->>Graph: Node 2: FinanceAgent (Determines getTransaction tool needed)

Graph->>Tools: Call getTransaction(txnId="CZUCW123")
activate Tools
Tools->>SB: GET /api/v1/transactions/CZUCW123 (Auth: Internal Bypass Header)
activate SB
SB-->>Tools: Returns JSON (merchantId="500100100014", status="FAILED", reversalPending=True)
deactivate SB
Tools-->>Graph: Return structured JSON
deactivate Tools

Graph->>Graph: Node 3: Validation Agent (Checks: does transaction merchantId match cscId?)
Note over Graph: Security check passes: 500100100014 matches session owner cscId

Graph->>Graph: Node 4: Response Agent (Summarizes status + triggers PII redaction)
Graph-->>GW: Return Final Response payload (response, intent, escalate=False)
deactivate Graph

GW->>Redis: Save updated history (Trimmed to last 10 messages)
GW-->>User: Stream JSON chunks + Final message package
deactivate GW
```
