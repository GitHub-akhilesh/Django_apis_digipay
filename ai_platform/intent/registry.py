from typing import List

INTENT_REGISTRY: List[str] = [
    # ---- Pre-existing DigiPay intents (unchanged) ----
    "CHECK_BALANCE",
    "CHECK_LIMITS",
    "MERCHANT_PROFILE",
    "MERCHANT_STATUS",
    "LEDGER_STATEMENT",
    "TXN_DETAILS",
    "TXN_REVERSAL",
    "PASSBOOK_VIEW",
    "NOTIFICATION_SEND",
    "AEPS_BALANCE",
    "AEPS_WITHDRAWAL",
    "SUPPORT_TICKET",
    "FAQ",
    "GENERAL",

    # ---- Intents covering the gateway-service read APIs ----
    "LEDGER_BALANCE",          # /v2/ledger/balance
    "LEDGER_PASSBOOK",         # /v2/ledger/passbook
    "LEDGER_RECOVERY",         # /v2/ledger/recovery/list
    "TXN_HISTORY",             # /v2/txn/logs
    "TXN_RESPONSE",            # /v2/txn/response
    "AEPS_HISTORY",            # /v2/aeps/logs, /balance-enquiry-list
    "AEPS_ENQUIRY_RESULT",     # /v2/aeps/balance-enquiry-response, *-details
    "NOTIFICATION_VIEW",       # /v2/notification/fetch
    "ANNOUNCEMENTS",           # /v2/notification/fetch/login
    "OPERATOR_LIST",           # /v2/operator/list/{cscId}
    "DEVICE_LIST",             # /v2/device/list
    "SERVICE_CATALOG",         # /v2/services/catalogs, /master-list
    "TXN_ANALYTICS",           # /api/v2/analytics
    "PAYOUT_STATUS",           # /v2/payout/status/{txnId}
    "DSP_TOPUP_STATUS",        # /v2/dsptopup/status/{txnId}
    "AUA_AUTH_STATUS",         # /v2/aua/status/{txnId}
    "UPI_VPA_SUGGESTION",      # /v1/upi/vpa/suggestion
    "PLATFORM_KEY",            # /v2/user/publickey
    "ADMIN_USER_DIRECTORY",    # /v2/admin/user/list, /details/{cscId}
    "ADMIN_REPORTS",           # /v2/admin/report, /dailytxnreport, /service-history
    "ADMIN_AUDIT",             # /v2/admin/user/login-journey, /block-history, /agent-auth
    "ADMIN_SETTLEMENT",        # /v2/admin/dsp-wallet-transfer/*
    "CAPABILITIES",            # "what can you do"

    # ---- Intents covering the legacy DigiPay API service (app/main.py) ----
    "LEGACY_TXN_LOGS",         # POST /api/v1/txn-logs
    "LEGACY_PASSBOOK",         # POST /api/v1/passbook
    "LEGACY_WALLET_BALANCE",   # POST /api/v1/wallet_balance

    # Requests the assistant is deliberately not able to fulfil (money movement,
    # writes, authentication). Routed to a clear explanation rather than a tool.
    "UNSUPPORTED_ACTION",
]
