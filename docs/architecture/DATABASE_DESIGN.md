# Database and Storage Design

The Enterprise AI Platform relies on two primary data stores: Redis (for short-term session conversation history) and Qdrant/Vector DB (for document embeddings).

---

## 1. Short-Term Memory: Redis

- **Key Pattern**: `ai_memory:session:{session_id}`
- **Data Structure**: String (JSON-serialized list of messages)
- **TTL Expiration**: 86,400 seconds (24 hours sliding window)

### Serialized JSON Schema:
```json
[
  {
    "role": "user",
    "content": "What is my wallet balance?",
    "timestamp": 1782012065
  },
  {
    "role": "assistant",
    "content": "Your active wallet balance is ₹4,560.50.",
    "intent": "Wallet",
    "policyChecked": true,
    "timestamp": 1782012066
  }
]
```

---

## 2. Long-Term Audit Log Store (Archival)

Archived conversation sessions are pushed to a relational schema (e.g. PostgreSQL) asynchronously via Kafka.

### `ai_audit_logs` Schema:
| Column Name | Data Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY | Unique audit trace ID |
| `session_id` | VARCHAR(50) | INDEX | Client-provided session tracking ID |
| `csc_id` | VARCHAR(45) | INDEX | Authenticated merchant VLE identifier |
| `user_message` | TEXT | | Raw incoming client query |
| `bot_response` | TEXT | | Sanitized output response returned to client |
| `intent` | VARCHAR(20) | | Classified intent category |
| `policy_checked`| BOOLEAN | | True if checked by Validation Agent |
| `escalated` | BOOLEAN | | True if handoff to Level 2/3 was requested |
| `trace_id` | VARCHAR(50) | | Zipkin correlation trace context ID |
| `duration_ms` | INTEGER | | Core roundtrip processing time |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Event timestamp |

---

## 3. Knowledge Base: Vector DB (Qdrant)

- **Collection Name**: `fintech_sops`
- **Vector Size**: 1536 (standard dimensions for `text-embedding-3-small`)
- **Metric**: Cosine Similarity

### Document Payload Schema:
```json
{
  "id": "uuid-v4",
  "vector": [0.0125, -0.0456, 0.0987, "..."],
  "payload": {
    "title": "AePS Cash Withdrawal Transaction Limits",
    "content": "Standard AePS single transaction limit is ₹10,000. Customer daily transaction count limits are capped at 5 withdrawals...",
    "category": "NPCI_SOP",
    "tags": ["aeps", "limits", "npci"],
    "version": "2.4",
    "updated_at": "2026-06-20T10:00:00Z"
  }
}
```
