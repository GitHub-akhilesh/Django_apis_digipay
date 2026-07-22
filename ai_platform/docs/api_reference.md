# DigiPay AI Platform API Reference Guide

This reference details the REST API specifications of the DigiPay AI Platform.

---

## 1. Chat & Orchestration APIs

### POST `/api/v1/chat/message`
Submit a message to the AI orchestrator.

* **Headers**: `Authorization: Bearer <JWT_TOKEN>`
* **Request Body**:
  ```json
  {
    "message": "What is my wallet balance?",
    "sessionId": "session-123",
    "cscId": "500100100014"
  }
  ```
* **Response Body**:
  ```json
  {
    "response": "Your wallet balance is ₹4560.50.",
    "intent": "Wallet",
    "explainability": {
      "intent": "Wallet",
      "selectedTools": ["getWalletBalance"],
      "executionTimeMs": 42.5
    }
  }
  ```

---

## 2. Admin & Settings APIs

### GET `/api/v1/admin/settings`
Returns active feature flags and app versions.

### PUT `/api/v1/admin/settings/flags`
Updates a feature flag value dynamically.
