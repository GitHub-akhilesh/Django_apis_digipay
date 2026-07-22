# Tool Adapter API Design

To maintain strict security and decoupling, the AI Platform *never* queries database tables directly. It interacts with data solely by calling endpoints exposed by the Spring Boot microservices.

---

## 1. Transaction API
- **Endpoint**: `GET /api/v1/transactions/{id}`
- **Description**: Returns detailed transaction records, including amounts, statuses, payment channels, and settlement tracking logs.
- **Expected Payload**:
```json
{
  "merchantId": "500100100014",
  "txnId": "CZUCW178186672384906DQQOQSU69890796",
  "status": "SUCCESS",
  "amount": 1000.00,
  "category": "AEPS",
  "type": "Cash Withdrawal",
  "mobile": "9988776655",
  "maskedAadhaar": "XXXX XXXX 6666",
  "rrn": "617016890796",
  "date": "2026-06-19 16:26:05",
  "disputed": false,
  "settlementStatus": "processed",
  "settlementDate": "2026-06-19 18:00:00",
  "utr": "UTR123456789"
}
```

---

## 2. Wallet API
- **Endpoint**: `GET /api/v1/wallets/{merchant_id}`
- **Description**: Retrieves wallet ledger balances and blocked balances.
- **Expected Payload**:
```json
{
  "merchantId": "500100100014",
  "balance": 4560.50,
  "blockedBalance": 120.00,
  "lastSettlementDate": "2026-07-19 18:30:00",
  "lastSettlementAmount": 1480.00
}
```

---

## 3. KYC API
- **Endpoint**: `GET /api/v1/kyc/{merchant_id}`
- **Description**: Fetches document verification flags and processor audit logs.
- **Expected Payload**:
```json
{
  "merchantId": "500100100014",
  "status": "APPROVED",
  "panNumber": "ABCDE1234F",
  "aadhaarNumber": "333344445555",
  "comments": "Documents verified manually.",
  "updatedAt": "2026-06-18 10:15:00"
}
```

---

## 4. Ticket/Complaint API
- **Endpoint**: `POST /api/v1/tickets`
- **Description**: Opens a dispute complaint ticket.
- **Payload Request**:
```json
{
  "merchantId": "500100100014",
  "category": "Refund",
  "details": "Failed transaction credit dispute."
}
```
- **Response**:
```json
{
  "ticketId": "TKT-1F89C0AB",
  "status": "OPEN",
  "createdAt": "2026-07-20 12:15:00"
}
```
