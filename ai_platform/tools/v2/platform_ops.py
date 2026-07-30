"""
Chat tools for the remaining read-only gateway controllers: notifications,
operators, devices, service catalogue, analytics, status lookups, UPI handle
suggestions and the platform public key.

Write routes on these controllers (notification create/delete, operator action,
device register/deregister, payout/top-up initiation, UPI onboarding and refund,
VATM and MATM transactions) are excluded in gateway.v2.safety.
"""

from typing import Optional

from gateway.v2.notification_client import notification_v2_client
from gateway.v2.platform_client import (
    analytics_v2_client,
    device_v2_client,
    external_partner_v2_client,
    operator_v2_client,
    service_catalog_v2_client,
    status_v2_client,
    upi_v2_client,
    user_v2_client,
)
from tools.decorator import SOURCE_GATEWAY_V2, tool

ALL_ROLES = ["ROLE_USER", "ROLE_MERCHANT", "ROLE_SUPPORT", "ROLE_ADMIN"]


# ---------------------------------------------------------------- notifications

@tool(
    name="getNotifications",
    description=(
        "In-app DigiPay notifications for a CSC ID. Filter by notification type and date range. "
        "Read-only — creating or deleting notifications is not available from chat."
    ),
    roles=ALL_ROLES,
    cacheable=True,
    ttl=30,
    domain="notification",
    source=SOURCE_GATEWAY_V2,
    endpoint="POST /v2/notification/fetch",
    examples=["any new notifications for me", "show my DigiPay alerts"],
)
async def get_notifications(
    csc_id: Optional[str] = None,
    notification_type: Optional[str] = None,
    notif_id: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    rpp: int = 10,
    cp: int = 1,
    jwt_token: str = None,
):
    return await notification_v2_client.fetch(
        jwt_token=jwt_token,
        csc_id=csc_id,
        notification_type=notification_type,
        notif_id=notif_id,
        from_date=from_date,
        to_date=to_date,
        rpp=rpp,
        cp=cp,
    )


@tool(
    name="getLoginNotifications",
    description="Broadcast DigiPay announcements shown on the login screen (platform-wide notices).",
    roles=ALL_ROLES,
    cacheable=True,
    ttl=300,
    domain="notification",
    source=SOURCE_GATEWAY_V2,
    endpoint="POST /v2/notification/fetch/login",
    examples=["any DigiPay announcements", "is there a planned outage"],
)
async def get_login_notifications(rpp: int = 10, cp: int = 1, jwt_token: str = None):
    return await notification_v2_client.fetch_login(jwt_token=jwt_token, rpp=rpp, cp=cp)


# -------------------------------------------------------- operators and devices

@tool(
    name="getOperatorList",
    description=(
        "List the operators registered under a 12-character CSC ID. Read-only — adding or "
        "modifying an operator must be done from the DigiPay portal."
    ),
    roles=ALL_ROLES,
    cacheable=True,
    ttl=60,
    domain="operator",
    source=SOURCE_GATEWAY_V2,
    endpoint="GET /v2/operator/list/{cscId}",
    examples=["list my operators", "how many operators do I have"],
)
async def get_operator_list(csc_id: str, jwt_token: str = None):
    return await operator_v2_client.list_operators(csc_id, jwt_token)


@tool(
    name="getDeviceList",
    description=(
        "List the biometric/RD devices registered against a CSC ID, with their status. "
        "Use this for 'is my fingerprint device registered', 'which devices are on my account'."
    ),
    roles=ALL_ROLES,
    cacheable=True,
    ttl=60,
    domain="device",
    source=SOURCE_GATEWAY_V2,
    endpoint="POST /v2/device/list",
    examples=["is my biometric device registered", "list my devices"],
)
async def get_device_list(
    csc_id: Optional[str] = None,
    device_type: Optional[str] = None,
    status: Optional[str] = None,
    rpp: int = 10,
    cp: int = 1,
    jwt_token: str = None,
):
    return await device_v2_client.list_devices(
        jwt_token=jwt_token,
        csc_id=csc_id,
        device_type=device_type,
        status=status,
        rpp=rpp,
        cp=cp,
    )


# ------------------------------------------------------------ service catalogue

@tool(
    name="getServiceCatalog",
    description=(
        "The DigiPay services enabled for the logged-in user, resolved from their JWT. "
        "Use this for 'which services can I use', 'is AePS enabled for me'."
    ),
    roles=ALL_ROLES,
    cacheable=True,
    ttl=300,
    domain="catalog",
    source=SOURCE_GATEWAY_V2,
    endpoint="GET /v2/services/catalogs",
    examples=["which services do I have access to", "is UPI enabled on my account"],
)
async def get_service_catalog(jwt_token: str = None):
    return await service_catalog_v2_client.catalogs(jwt_token)


@tool(
    name="getMasterServiceList",
    description="The master catalogue of every DigiPay service, independent of a specific user.",
    roles=ALL_ROLES,
    cacheable=True,
    ttl=600,
    domain="catalog",
    source=SOURCE_GATEWAY_V2,
    endpoint="GET /v2/services/master-list",
    examples=["what services does DigiPay offer"],
)
async def get_master_service_list(jwt_token: str = None):
    return await service_catalog_v2_client.master_list(jwt_token)


# ------------------------------------------------------------------- analytics

@tool(
    name="getTxnAnalytics",
    description=(
        "Aggregated transaction analytics — counts, values, success/failure split and "
        "commission for a CSC ID over a date range. Use this for 'how much did I earn', "
        "'summary of my business this month'."
    ),
    roles=ALL_ROLES,
    cacheable=True,
    ttl=120,
    domain="analytics",
    source=SOURCE_GATEWAY_V2,
    endpoint="POST /api/v2/analytics",
    examples=["summarise my transactions this month", "how much commission did I earn"],
)
async def get_txn_analytics(
    csc_id: Optional[str] = None,
    type: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    result_type: Optional[str] = None,
    jwt_token: str = None,
):
    return await analytics_v2_client.analytics(
        jwt_token=jwt_token,
        csc_id=csc_id,
        type=type,
        from_date=from_date,
        to_date=to_date,
        result_type=result_type,
    )


# -------------------------------------------------------------- status lookups

@tool(
    name="getPayoutStatusV2",
    description=(
        "Settlement status of a payout by transaction ID, read from the payout service. "
        "Status check only — initiating or refunding a payout is not available from chat."
    ),
    roles=ALL_ROLES,
    cacheable=True,
    ttl=20,
    domain="payout",
    source=SOURCE_GATEWAY_V2,
    endpoint="GET /v2/payout/status/{txnId}",
    examples=["status of payout PAY123456", "has my settlement been credited"],
)
async def get_payout_status_v2(txn_id: str, jwt_token: str = None):
    return await status_v2_client.payout_status(txn_id, jwt_token)


@tool(
    name="getDspTopUpStatus",
    description="Status of a DSP top-up by transaction ID. Status check only.",
    roles=ALL_ROLES,
    cacheable=True,
    ttl=20,
    domain="payout",
    source=SOURCE_GATEWAY_V2,
    endpoint="GET /v2/dsptopup/status/{txnId}",
    examples=["status of my DSP top-up DSP123456"],
)
async def get_dsp_topup_status(txn_id: str, jwt_token: str = None):
    return await status_v2_client.dsp_topup_status(txn_id, jwt_token)


@tool(
    name="getAuaAuthStatus",
    description=(
        "Status of an Aadhaar (AUA) biometric authentication attempt by transaction ID. "
        "Optionally narrow by service category. Reads a past attempt — it cannot authenticate."
    ),
    roles=ALL_ROLES,
    cacheable=True,
    ttl=20,
    domain="aua",
    source=SOURCE_GATEWAY_V2,
    endpoint="GET /v2/aua/status/{txnId}",
    examples=["did my Aadhaar authentication succeed for txn AUA123"],
)
async def get_aua_auth_status(txn_id: str, category: Optional[str] = None, jwt_token: str = None):
    return await status_v2_client.aua_status(txn_id, category, jwt_token)


# --------------------------------------------------------- platform utilities

@tool(
    name="getUpiVpaSuggestions",
    description=(
        "Available UPI VPA (virtual payment address) handle suggestions. Read-only — "
        "creating a UPI merchant or generating a payable QR is not available from chat."
    ),
    roles=ALL_ROLES,
    cacheable=True,
    ttl=300,
    domain="upi",
    source=SOURCE_GATEWAY_V2,
    endpoint="GET /v1/upi/vpa/suggestion",
    examples=["what UPI handles can I use"],
)
async def get_upi_vpa_suggestions(jwt_token: str = None):
    return await upi_v2_client.vpa_suggestion(jwt_token)


@tool(
    name="getMyProfile",
    description=(
        "The signed-in user's own DigiPay profile: name, mobile, CSC details, bank "
        "account and IFSC, KYC state, and the services enabled on the account. Use "
        "this for 'about me', 'my profile', 'my bank details', 'my KYC status'."
    ),
    roles=ALL_ROLES,
    cacheable=True,
    ttl=60,
    domain="profile",
    source=SOURCE_GATEWAY_V2,
    endpoint="POST /v2/user/check-profile",
    examples=["tell me about my account", "what are my bank details", "what is my KYC status"],
)
async def get_my_profile(csc_id: str, owner_id: str = None, role: str = None, jwt_token: str = None):
    return await user_v2_client.my_profile(
        csc_id=csc_id, owner_id=owner_id, role=role, jwt_token=jwt_token
    )


@tool(
    name="getPlatformPublicKey",
    description="The active DigiPay RSA public key used to encrypt API request payloads.",
    roles=["ROLE_SUPPORT", "ROLE_ADMIN"],
    cacheable=True,
    ttl=600,
    domain="platform",
    source=SOURCE_GATEWAY_V2,
    endpoint="GET /v2/user/publickey",
    examples=["what is the current DigiPay public key"],
)
async def get_platform_public_key(jwt_token: str = None):
    return await user_v2_client.public_key(jwt_token)


@tool(
    name="adminGetExternalVleBalance",
    description=(
        "VLE ledger balance as reported to external partner clients, via the partner "
        "client API. Administrator use only."
    ),
    roles=["ROLE_ADMIN"],
    cacheable=True,
    ttl=30,
    domain="admin",
    source=SOURCE_GATEWAY_V2,
    endpoint="POST /v2/api/client/vle/balance",
    examples=["what balance does the partner API report for 500100100014"],
)
async def admin_get_external_vle_balance(
    csc_id: str, client_id: Optional[str] = None, jwt_token: str = None
):
    return await external_partner_v2_client.vle_balance(csc_id, client_id, jwt_token)
