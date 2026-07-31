"""
Read-Only Allow-List for the DigiPay Spring Boot Gateway (gateway-service).

WHY THIS FILE EXISTS
--------------------
The chat assistant is only ever permitted to *read* from the DigiPay gateway.
It must never initiate a transaction, move money, register/deregister a device,
create/update/delete a record, authenticate a customer, or send an OTP.

Rather than relying on reviewers to notice a bad call site, every request made
through `gateway.v2.base.GatewayV2Client` is checked against ALLOWED_ENDPOINTS
below. A path that is not explicitly listed cannot be called at all — adding a
mutating endpoint requires editing this file, which is the audit point.

EXCLUDED_ENDPOINTS is not dead weight: it is the deliberate, reviewable record
of which gateway endpoints were examined and consciously kept out of chat, so a
future maintainer does not mistake an omission for an oversight.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple

from core.exceptions import AuthenticationException

logger = logging.getLogger("ai_platform.gateway.v2.safety")


class EndpointSpec:
    """A single gateway endpoint the assistant is allowed to read from."""

    def __init__(
        self,
        method: str,
        path: str,
        controller: str,
        summary: str,
        roles: Optional[List[str]] = None,
    ):
        self.method = method.upper()
        self.path = path
        self.controller = controller
        self.summary = summary
        self.roles = roles or ["ROLE_USER", "ROLE_MERCHANT", "ROLE_SUPPORT", "ROLE_ADMIN"]

    @property
    def key(self) -> str:
        return f"{self.method} {self.path}"

    def matches(self, method: str, path: str) -> bool:
        """Compare a concrete request against this (possibly templated) spec."""
        if method.upper() != self.method:
            return False
        # Build "^/v2/admin/details/[^/]+$" from "/v2/admin/details/{cscId}",
        # escaping the literal segments so no path character is treated as regex.
        parts = [
            "[^/]+" if (p.startswith("{") and p.endswith("}")) else re.escape(p)
            for p in self.path.split("/")
        ]
        return re.fullmatch("/".join(parts), path) is not None


# ---------------------------------------------------------------------------
# ALLOWED — read-only gateway endpoints exposed to chat.
# ---------------------------------------------------------------------------
ALLOWED_ENDPOINTS: List[EndpointSpec] = [
    # ---------------- AdminController (/v2/admin) ----------------
    EndpointSpec("POST", "/v2/admin/user/list", "AdminController",
                 "Paginated VLE/user directory search", ["ROLE_ADMIN"]),
    EndpointSpec("POST", "/v2/admin/dailytxnreport", "AdminController",
                 "Daily transaction volume/value report", ["ROLE_ADMIN"]),
    EndpointSpec("GET", "/v2/admin/txn-details", "AdminController",
                 "Transaction details by reference number and category", ["ROLE_ADMIN", "ROLE_SUPPORT"]),
    EndpointSpec("POST", "/v2/admin/report", "AdminController",
                 "Consolidated admin report (JSON)", ["ROLE_ADMIN"]),
    EndpointSpec("POST", "/v2/admin/profileDetails/orpList", "AdminController",
                 "Profile details with operator list", ["ROLE_ADMIN"]),
    EndpointSpec("GET", "/v2/admin/details/{cscId}", "AdminController",
                 "Full user/VLE record for a CSC ID", ["ROLE_ADMIN"]),
    EndpointSpec("POST", "/v2/admin/user/login-journey", "AdminController",
                 "Login journey audit trail for a user", ["ROLE_ADMIN"]),
    EndpointSpec("POST", "/v2/admin/user/block-history", "AdminController",
                 "Block/unblock history for a user", ["ROLE_ADMIN"]),
    EndpointSpec("POST", "/v2/admin/user/operators", "AdminController",
                 "Operators mapped to a user", ["ROLE_ADMIN"]),
    EndpointSpec("POST", "/v2/admin/user/agent-auth", "AdminController",
                 "Agent (VLE) biometric authentication logs", ["ROLE_ADMIN"]),
    EndpointSpec("POST", "/v2/admin/service-history", "AdminController",
                 "Per-service usage history for a user", ["ROLE_ADMIN"]),
    EndpointSpec("POST", "/v2/admin/timeout/list", "AdminController",
                 "AePS timed-out transaction list", ["ROLE_ADMIN"]),
    # A read despite being a POST, like most listings on this gateway:
    # AdminController.listServiceStatusSchedules only forwards a filter. Its two
    # siblings (schedule, schedule/cancel) mutate and are in EXCLUDED_ENDPOINTS.
    EndpointSpec("POST", "/v2/admin/service-status/schedule/list", "AdminController",
                 "Scheduled service up/down windows (planned maintenance)", ["ROLE_ADMIN"]),
    EndpointSpec("POST", "/v2/admin/dsp-wallet-transfer/logs", "AdminController",
                 "DSP wallet transfer logs", ["ROLE_ADMIN"]),
    EndpointSpec("GET", "/v2/admin/dsp-wallet-transfer/{txnId}", "AdminController",
                 "DSP wallet transfer detail by txnId", ["ROLE_ADMIN"]),
    EndpointSpec("POST", "/v2/admin/dsp-wallet-transfer/daily-settlement", "AdminController",
                 "DSP daily settlement listing", ["ROLE_ADMIN"]),

    # ---------------- AepsController (/v2/aeps) — read paths only ----------------
    EndpointSpec("GET", "/v2/aeps/balance-enquiry-response", "AepsController",
                 "AePS balance enquiry result for a reference number"),
    EndpointSpec("POST", "/v2/aeps/balance-enquiry-list", "AepsController",
                 "Paginated AePS balance enquiry history"),
    EndpointSpec("POST", "/v2/aeps/balance-enquiry-details", "AepsController",
                 "AePS balance enquiry detail by txnId or RRN"),
    EndpointSpec("POST", "/v2/aeps/logs", "AepsController",
                 "Paginated AePS transaction logs"),
    EndpointSpec("POST", "/v2/aeps/log-details", "AepsController",
                 "AePS transaction log detail by txnId or RRN"),

    # ---------------- TxnLogController (/v2/txn) ----------------
    EndpointSpec("POST", "/v2/txn/logs", "TxnLogController",
                 "Paginated transaction log search across services"),
    EndpointSpec("GET", "/v2/txn/response", "TxnLogController",
                 "Raw switch/bank response for a transaction reference"),

    # ---------------- LedgerController (/v2/ledger) — read paths only ----------------
    EndpointSpec("GET", "/v2/ledger/balance", "LedgerController",
                 "Ledger (wallet) balance enquiry for a CSC ID"),
    EndpointSpec("POST", "/v2/ledger/passbook", "LedgerController",
                 "Ledger passbook entries with filters and pagination"),
    EndpointSpec("POST", "/v2/ledger/recovery/list", "LedgerController",
                 "Ledger recovery case listing", ["ROLE_ADMIN"]),

    # ---------------- NotificationController (/v2/notification) — read paths only ----------------
    EndpointSpec("POST", "/v2/notification/fetch", "NotificationController",
                 "In-app notifications for a user"),
    EndpointSpec("POST", "/v2/notification/fetch/login", "NotificationController",
                 "Login-screen broadcast notifications"),

    # ---------------- OperatorController (/v2/operator) — read paths only ----------------
    EndpointSpec("GET", "/v2/operator/list/{cscId}", "OperatorController",
                 "Operators registered under a CSC ID"),

    # ---------------- DeviceGatewayController (/v2/device) — read paths only ----------------
    EndpointSpec("POST", "/v2/device/list", "DeviceGatewayController",
                 "Registered biometric/RD devices for a CSC ID"),

    # ---------------- ServiceCatalogGatewayController (/v2/services) ----------------
    EndpointSpec("GET", "/v2/services/catalogs", "ServiceCatalogGatewayController",
                 "Services enabled for the logged-in user"),
    EndpointSpec("GET", "/v2/services/master-list", "ServiceCatalogGatewayController",
                 "Master catalogue of all DigiPay services"),

    # ---------------- AnalyticsController (/api/v2) ----------------
    EndpointSpec("POST", "/api/v2/analytics", "AnalyticsController",
                 "Aggregated transaction analytics"),

    # ---------------- Status lookups (read-only GETs) ----------------
    EndpointSpec("GET", "/v2/payout/status/{txnId}", "PayOutController",
                 "Payout (IMPS/NEFT) settlement status by txnId"),
    EndpointSpec("GET", "/v2/dsptopup/status/{txnId}", "DspTopUpController",
                 "DSP top-up status by txnId"),
    EndpointSpec("GET", "/v2/aua/status/{txnId}", "AuaAuthController",
                 "Aadhaar AUA biometric authentication status by txnId"),

    # ---------------- UPIController (/v1/upi) — read paths only ----------------
    EndpointSpec("GET", "/v1/upi/vpa/suggestion", "UPIController",
                 "Available UPI VPA (handle) suggestions"),

    # ---------------- UserController (/v2/user) — read paths only ----------------
    EndpointSpec("GET", "/v2/user/publickey", "UserController",
                 "Active RSA public key used for payload encryption"),
    # /check-profile reads the signed-in user's own profile: name, bank details,
    # KYC state and enabled services. Despite the name it authenticates nothing —
    # it validates the body and forwards to the user service, and the DigiPay web
    # app calls it AFTER login (with mode="sync") purely to populate the profile
    # screen. Token issuance lives in /generate-otp and /validate-otp, which stay
    # excluded. Called here only with mode="sync".
    EndpointSpec("POST", "/v2/user/check-profile", "UserController",
                 "Signed-in user's own profile, bank details and enabled services"),

    # ---------------- ExternalClientController (/v2/api/client) — read paths only ----------------
    EndpointSpec("POST", "/v2/api/client/vle/balance", "ExternalClientController",
                 "VLE ledger balance for an external partner client", ["ROLE_ADMIN"]),
]

ALLOWED_INDEX: Dict[str, EndpointSpec] = {spec.key: spec for spec in ALLOWED_ENDPOINTS}


# ---------------------------------------------------------------------------
# EXCLUDED — reviewed and deliberately NOT wired into chat.
#
# Reason codes:
#   MONEY_MOVEMENT  initiates or settles a financial transaction
#   WRITE           creates, updates or deletes a record
#   AUTH            authenticates a person / issues or validates an OTP
#   CALLBACK        inbound switch/partner callback, not user-facing
#   UNSUPPORTED     transport chat cannot serve (SSE, multipart, binary, crypto payload)
# ---------------------------------------------------------------------------
EXCLUDED_ENDPOINTS: List[Tuple[str, str, str, str]] = [
    ("POST", "/v2/ledger/deposit", "MONEY_MOVEMENT", "Credits a ledger account"),
    ("POST", "/v2/ledger/withdrawal", "MONEY_MOVEMENT", "Debits a ledger account"),
    ("POST", "/v2/ledger/recovery", "MONEY_MOVEMENT", "Recovers funds from a VLE ledger"),
    ("POST", "/v2/ledger/transfer", "MONEY_MOVEMENT", "Wallet-to-wallet fund transfer"),
    ("POST", "/v2/aeps/balance-enquiry", "MONEY_MOVEMENT", "Initiates a live AePS biometric enquiry at the switch"),
    ("POST", "/v2/aeps/cash-withdrawal", "MONEY_MOVEMENT", "AePS cash withdrawal"),
    ("POST", "/v2/aeps/cash-deposit", "MONEY_MOVEMENT", "AePS cash deposit"),
    ("POST", "/v2/aeps/mini-statement", "MONEY_MOVEMENT", "Live AePS mini statement at the switch"),
    ("POST", "/v2/aeps/reqotp", "AUTH", "Requests a customer OTP"),
    ("POST", "/v2/payout/init", "MONEY_MOVEMENT", "Initiates a payout"),
    ("POST", "/v2/payout/admin/refund", "MONEY_MOVEMENT", "Refunds a payout"),
    ("POST", "/v2/dsptopup/init", "MONEY_MOVEMENT", "Initiates a DSP top-up"),
    ("POST", "/v2/dsptopup/init/dsp-txn-tnf", "MONEY_MOVEMENT", "Initiates DSP daily settlement transfer"),
    ("POST", "/v2/vatm/transactions", "MONEY_MOVEMENT", "VATM withdrawal transaction"),
    ("GET", "/v2/vatm/merchantcreation", "WRITE", "Creates a VATM merchant"),
    ("POST", "/v2/admin/service-status/schedule", "WRITE",
     "Schedules a service up/down window — changes what VLEs can transact on"),
    ("POST", "/v2/admin/service-status/schedule/cancel", "WRITE",
     "Cancels a scheduled service status window"),
    ("POST", "/v2/matm/transaction/init", "MONEY_MOVEMENT", "MATM transaction initiation"),
    ("POST", "/api/thirdparty/credit/process", "MONEY_MOVEMENT", "Third-party credit processing"),
    ("POST", "/v1/upi/refund", "MONEY_MOVEMENT", "UPI refund"),
    ("POST", "/v1/upi/merchant/onboarding", "WRITE", "Creates a UPI merchant"),
    ("POST", "/v1/upi/dynamicQrGeneration", "WRITE", "Generates a payable dynamic QR"),
    ("POST", "/v1/upi/merchant/activate", "WRITE", "Activates a UPI merchant"),
    ("POST", "/v1/upi/merchant/deactivate", "WRITE", "Deactivates a UPI merchant"),
    ("POST", "/v2/admin/block", "WRITE", "Blocks/unblocks user or service access"),
    ("POST", "/v2/admin/api/enquiry", "WRITE", "Switch enquiry that reconciles and mutates transaction state"),
    ("POST", "/v2/device/register", "WRITE", "Registers a biometric device"),
    ("POST", "/v2/device/deregister", "WRITE", "Deregisters a biometric device"),
    ("POST", "/v2/notification/delete", "WRITE", "Deletes a notification"),
    ("POST", "/v2/notification/create", "WRITE", "Creates a notification (multipart)"),
    ("POST", "/v2/operator/action", "WRITE", "Adds/modifies an operator"),
    ("POST", "/v2/location/sync", "WRITE", "Persists device geolocation"),
    ("POST", "/v2/location/validate", "WRITE", "Pre-transaction geo-fencing gate"),
    ("POST", "/v2/aua/bio-auth", "AUTH", "Aadhaar biometric authentication"),
    ("POST", "/v2/user/generate-otp", "AUTH", "Generates a login OTP"),
    ("POST", "/v2/user/validate-otp", "AUTH", "Validates a login OTP and issues a session"),
    ("POST", "/v2/user/logout", "AUTH", "Terminates a session"),
    ("GET", "/v2/user/connectLogin/{uuid}", "AUTH", "CSC Connect SSO login"),
    ("POST", "/v2/user/consume-connect-view", "AUTH", "Consumes a CSC Connect view token"),
    ("POST", "/v2/api/client/vle/block", "WRITE", "Blocks a VLE via partner client"),
    ("POST", "/v1/upi/collect/tvp", "CALLBACK", "UPI collect callback"),
    ("POST", "/v1/upi/callback/inward", "CALLBACK", "UPI inward payment callback"),
    ("POST", "/v2/matm/iserveu/callback", "CALLBACK", "MATM iServeU callback"),
    ("POST", "/v2/matm/eureka/callback", "CALLBACK", "MATM Eureka callback"),
    ("GET", "/v1/upi/payment/events/{transactionId}", "UNSUPPORTED", "Server-Sent Events stream"),
    ("GET", "/v2/notification/image/**", "UNSUPPORTED", "Binary image download"),
    ("POST", "/api/v2/txn-status", "UNSUPPORTED", "Salesforce endpoint requiring an encrypted payload"),
]


def resolve_endpoint(method: str, path: str) -> EndpointSpec:
    """
    Resolve a concrete (method, path) to its allow-listed spec.

    Raises AuthenticationException when the endpoint is not on the read-only
    allow-list, naming the exclusion reason when one is recorded.
    """
    for spec in ALLOWED_ENDPOINTS:
        if spec.matches(method, path):
            return spec

    for ex_method, ex_path, reason, note in EXCLUDED_ENDPOINTS:
        if ex_method == method.upper() and ex_path == path:
            logger.error(
                "BLOCKED: chat attempted a non-read gateway call %s %s (%s: %s)",
                method, path, reason, note
            )
            raise AuthenticationException(
                f"Blocked: '{method.upper()} {path}' is excluded from the assistant "
                f"({reason} — {note}). Only read-only gateway endpoints are callable."
            )

    logger.error("BLOCKED: chat attempted an unlisted gateway call %s %s", method, path)
    raise AuthenticationException(
        f"Blocked: '{method.upper()} {path}' is not on the read-only gateway allow-list."
    )


def describe_allow_list() -> List[Dict[str, object]]:
    """Machine-readable allow-list, surfaced by the governance API."""
    return [
        {
            "method": spec.method,
            "path": spec.path,
            "controller": spec.controller,
            "summary": spec.summary,
            "roles": spec.roles,
        }
        for spec in ALLOWED_ENDPOINTS
    ]


def describe_exclusions() -> List[Dict[str, str]]:
    """Machine-readable exclusion register, surfaced by the governance API."""
    return [
        {"method": m, "path": p, "reason": reason, "note": note}
        for m, p, reason, note in EXCLUDED_ENDPOINTS
    ]
