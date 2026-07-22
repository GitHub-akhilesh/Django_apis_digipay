# DigiPay AI Platform Troubleshooting Guide

This guide documents the error code reference, trace logging instructions, and failure resolution workflows.

---

## 1. Error Code Reference

| Error Code | Class | Cause | Resolution |
|---|---|---|---|
| `SEC-403` | `SecurityException` | Adversarial injection pattern or PII bypass detected. | Review query parameters and sanitize inputs. |
| `AUTH-401`| `AuthenticationException` | Invalid or expired JWT token. | Re-authenticate client VLE to get fresh JWT token. |
| `TOOL-500`| `ToolExecutionException` | Downstream service validation failure or timeout. | Verify Springfield gateway client endpoints health logs. |

## 2. Dynamic Circuit Breakers

If the downstream gateway services become slow:
* The circuit breaker opens after 5 failures in a 30-second window.
* Subsequent calls immediately fail fast with `TOOL-500` until recovery is detected in half-open status.
