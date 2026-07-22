# Security and Compliance Guidelines

This document details the security safeguards built into the Enterprise AI Support Platform to ensure regulatory compliance and strict data isolation.

---

## 1. Authentication & Session Context

- All client entrypoints (WebSockets or Server-Sent Events) **must** require a valid JWT token issued by the enterprise authentication service.
- The WebSocket connection handshake reads the token from the query parameters, decodes it using the shared secret (`JWT_SECRET`), and binds the validated `cscId` context directly to the socket session.
- If the token is missing, expired, or invalid, the socket connection is rejected with a `401 Unauthorized` equivalent code (WS status code 1008 - Policy Violation) and terminated.

---

## 2. Multi-Tenant Data Isolation (RBAC)

The AI orchestrator employs a designated **Validation Agent** node positioned between the tool executor and the final response generator to enforce tenant isolation:
- Every data object returned by the Spring Boot backend APIs is evaluated by the Validation Agent.
- The agent extracts ownership markers (e.g. `merchantId`, `user_id`, or `cscId`) from the tool outcome records.
- If the owner of the returned record does not match the authenticated session's `cscId`, the Validation Agent **blocks** the transaction, overrides the response with an access warning, and flags the session for human security escalation (`escalate = True`).
- This design completely prevents malicious users from querying details of another merchant's transactions.

---

## 3. PII Scrubbing and Redaction

To maintain NPCI compliance and safeguard customer privacy, the **Response Agent** processes all final conversational replies through a PII Redaction Engine:
- **Aadhaar Cards**: Matches 12-digit patterns (continuous or space-separated) and masks them to the format: `XXXX XXXX 1234` (preserving only the last 4 digits).
- **Mobile Numbers**: Identifies 10-digit telephone patterns and masks them to: `XXXXXXX123` (preserving only the final 3 digits).
- **Bank Accounts**: Replaces account numbers with masked forms in the response output.
