"""
Chat tools for AdminController (/v2/admin) — read-only reporting.

Every tool here is restricted to ROLE_ADMIN (with ROLE_SUPPORT added only for
cross-service transaction lookup, which support agents need to answer tickets).
The block/unblock and switch-enquiry routes on the same controller mutate state
and are excluded in gateway.v2.safety.
"""

from typing import Optional

from gateway.v2.admin_client import admin_v2_client
from tools.decorator import SOURCE_GATEWAY_V2, tool

ADMIN_ONLY = ["ROLE_ADMIN"]
ADMIN_SUPPORT = ["ROLE_ADMIN", "ROLE_SUPPORT"]


@tool(
    name="adminGetUserList",
    description=(
        "Search the DigiPay VLE/user directory. Filter by free-text search, state code, "
        "district code, role, active status or registration date range. Paginated."
    ),
    roles=ADMIN_ONLY,
    cacheable=True,
    ttl=60,
    domain="admin",
    source=SOURCE_GATEWAY_V2,
    endpoint="POST /v2/admin/user/list",
    examples=["list VLEs in Bihar", "search users named Sharma", "show blocked users"],
)
async def admin_get_user_list(
    search: Optional[str] = None,
    state_code: Optional[int] = None,
    district_code: Optional[int] = None,
    role: Optional[str] = None,
    active_status: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    rpp: int = 10,
    cp: int = 1,
    jwt_token: str = None,
):
    return await admin_v2_client.user_list(
        jwt_token=jwt_token,
        search=search,
        state_code=state_code,
        district_code=district_code,
        role=role,
        active_status=active_status,
        from_date=from_date,
        to_date=to_date,
        rpp=rpp,
        cp=cp,
    )


@tool(
    name="adminGetUserDetails",
    description="Fetch the full DigiPay user/VLE record for one 12-character CSC ID.",
    roles=ADMIN_ONLY,
    cacheable=True,
    ttl=60,
    domain="admin",
    source=SOURCE_GATEWAY_V2,
    endpoint="GET /v2/admin/details/{cscId}",
    examples=["show details for CSC ID 500100100014"],
)
async def admin_get_user_details(csc_id: str, jwt_token: str = None):
    return await admin_v2_client.user_details(csc_id, jwt_token)


@tool(
    name="adminGetDailyTxnReport",
    description=(
        "Daily transaction report giving per-day counts and values by service. "
        "Filter by CSC ID, service type and date range."
    ),
    roles=ADMIN_ONLY,
    cacheable=True,
    ttl=120,
    domain="admin",
    source=SOURCE_GATEWAY_V2,
    endpoint="POST /v2/admin/dailytxnreport",
    examples=["daily transaction report for last week", "yesterday's AePS volumes"],
)
async def admin_get_daily_txn_report(
    csc_id: Optional[str] = None,
    type: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    rpp: int = 10,
    cp: int = 1,
    jwt_token: str = None,
):
    return await admin_v2_client.daily_txn_report(
        jwt_token=jwt_token,
        csc_id=csc_id,
        type=type,
        from_date=from_date,
        to_date=to_date,
        rpp=rpp,
        cp=cp,
    )


@tool(
    name="adminGetReport",
    description=(
        "Consolidated administrative report across DigiPay services. Filter by CSC ID, "
        "service type, status and date range."
    ),
    roles=ADMIN_ONLY,
    cacheable=True,
    ttl=120,
    domain="admin",
    source=SOURCE_GATEWAY_V2,
    endpoint="POST /v2/admin/report",
    examples=["consolidated report for June", "failed transactions report"],
)
async def admin_get_report(
    csc_id: Optional[str] = None,
    type: Optional[str] = None,
    status: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    rpp: int = 10,
    cp: int = 1,
    jwt_token: str = None,
):
    return await admin_v2_client.report(
        jwt_token=jwt_token,
        csc_id=csc_id,
        type=type,
        status=status,
        from_date=from_date,
        to_date=to_date,
        rpp=rpp,
        cp=cp,
    )


@tool(
    name="adminGetTxnDetails",
    description=(
        "Look up a single transaction across DigiPay services by reference number. "
        "Requires the service category, for example AEPS_CASH_WITHDRAWAL, PAYOUT, "
        "DSP_TOPUP, VATM_WITHDRAWAL or UPI_CASH_WITHDRAWAL."
    ),
    roles=ADMIN_SUPPORT,
    cacheable=True,
    ttl=30,
    domain="admin",
    source=SOURCE_GATEWAY_V2,
    endpoint="GET /v2/admin/txn-details",
    examples=["find transaction RRN 512345678901 for AePS withdrawal"],
)
async def admin_get_txn_details(ref_no: str, type: str, jwt_token: str = None):
    return await admin_v2_client.txn_details(ref_no, type, jwt_token)


@tool(
    name="adminGetProfileOperatorList",
    description="Fetch a VLE profile together with the operators mapped to it.",
    roles=ADMIN_ONLY,
    cacheable=True,
    ttl=60,
    domain="admin",
    source=SOURCE_GATEWAY_V2,
    endpoint="POST /v2/admin/profileDetails/orpList",
    examples=["profile and operators for 500100100014"],
)
async def admin_get_profile_operator_list(csc_id: str, jwt_token: str = None):
    return await admin_v2_client.profile_operator_list(csc_id, jwt_token)


@tool(
    name="adminGetLoginJourney",
    description="Login journey audit trail for a user — each login stage, device and outcome.",
    roles=ADMIN_ONLY,
    cacheable=True,
    ttl=60,
    domain="admin",
    source=SOURCE_GATEWAY_V2,
    endpoint="POST /v2/admin/user/login-journey",
    examples=["login journey for 500100100014 yesterday"],
)
async def admin_get_login_journey(
    csc_id: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    status: Optional[str] = None,
    rpp: int = 10,
    cp: int = 1,
    jwt_token: str = None,
):
    return await admin_v2_client.login_journey(
        jwt_token=jwt_token,
        csc_id=csc_id,
        from_date=from_date,
        to_date=to_date,
        status=status,
        rpp=rpp,
        cp=cp,
    )


@tool(
    name="adminGetBlockHistory",
    description=(
        "History of block and unblock actions taken on a user or service. "
        "Read-only: blocking access itself is not available from chat."
    ),
    roles=ADMIN_ONLY,
    cacheable=True,
    ttl=60,
    domain="admin",
    source=SOURCE_GATEWAY_V2,
    endpoint="POST /v2/admin/user/block-history",
    examples=["why was 500100100014 blocked", "block history for last month"],
)
async def admin_get_block_history(
    csc_id: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    rpp: int = 10,
    cp: int = 1,
    jwt_token: str = None,
):
    return await admin_v2_client.block_history(
        jwt_token=jwt_token,
        csc_id=csc_id,
        from_date=from_date,
        to_date=to_date,
        rpp=rpp,
        cp=cp,
    )


@tool(
    name="adminGetUserOperators",
    description="List the operators mapped to a given user, from the admin service.",
    roles=ADMIN_ONLY,
    cacheable=True,
    ttl=60,
    domain="admin",
    source=SOURCE_GATEWAY_V2,
    endpoint="POST /v2/admin/user/operators",
    examples=["operators under 500100100014"],
)
async def admin_get_user_operators(
    csc_id: Optional[str] = None,
    search: Optional[str] = None,
    rpp: int = 10,
    cp: int = 1,
    jwt_token: str = None,
):
    return await admin_v2_client.user_operators(
        jwt_token=jwt_token, csc_id=csc_id, search=search, rpp=rpp, cp=cp
    )


@tool(
    name="adminGetAgentAuthLogs",
    description=(
        "Agent (VLE) biometric authentication attempt logs. Filter by CSC ID, "
        "the service the authentication was for (authFor), and date range."
    ),
    roles=ADMIN_ONLY,
    cacheable=True,
    ttl=60,
    domain="admin",
    source=SOURCE_GATEWAY_V2,
    endpoint="POST /v2/admin/user/agent-auth",
    examples=["agent auth failures today", "agent auth logs for 500100100014"],
)
async def admin_get_agent_auth_logs(
    csc_id: Optional[str] = None,
    auth_for: Optional[str] = None,
    status: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    rpp: int = 10,
    cp: int = 1,
    jwt_token: str = None,
):
    return await admin_v2_client.agent_auth_logs(
        jwt_token=jwt_token,
        csc_id=csc_id,
        auth_for=auth_for,
        status=status,
        from_date=from_date,
        to_date=to_date,
        rpp=rpp,
        cp=cp,
    )


@tool(
    name="adminGetServiceHistory",
    description="Per-service usage history for a user — which DigiPay services were used and how often.",
    roles=ADMIN_ONLY,
    cacheable=True,
    ttl=120,
    domain="admin",
    source=SOURCE_GATEWAY_V2,
    endpoint="POST /v2/admin/service-history",
    examples=["service history for 500100100014"],
)
async def admin_get_service_history(
    csc_id: Optional[str] = None,
    type: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    rpp: int = 10,
    cp: int = 1,
    jwt_token: str = None,
):
    return await admin_v2_client.service_history(
        jwt_token=jwt_token,
        csc_id=csc_id,
        type=type,
        from_date=from_date,
        to_date=to_date,
        rpp=rpp,
        cp=cp,
    )


@tool(
    name="adminGetTimeoutTxnList",
    description="AePS transactions that timed out at the switch and may need reconciliation.",
    roles=ADMIN_ONLY,
    cacheable=True,
    ttl=60,
    domain="admin",
    source=SOURCE_GATEWAY_V2,
    endpoint="POST /v2/admin/timeout/list",
    examples=["timed out AePS transactions today"],
)
async def admin_get_timeout_txn_list(
    csc_id: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    rpp: int = 10,
    cp: int = 1,
    jwt_token: str = None,
):
    return await admin_v2_client.timeout_txn_list(
        jwt_token=jwt_token, csc_id=csc_id, from_date=from_date, to_date=to_date, rpp=rpp, cp=cp
    )


@tool(
    name="adminGetDspWalletTransferLogs",
    description="DSP wallet transfer logs, filterable by CSC ID, status, UTR and date range.",
    roles=ADMIN_ONLY,
    cacheable=True,
    ttl=60,
    domain="admin",
    source=SOURCE_GATEWAY_V2,
    endpoint="POST /v2/admin/dsp-wallet-transfer/logs",
    examples=["DSP wallet transfers this week"],
)
async def admin_get_dsp_wallet_transfer_logs(
    csc_id: Optional[str] = None,
    status: Optional[str] = None,
    utr: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    rpp: int = 10,
    cp: int = 1,
    jwt_token: str = None,
):
    return await admin_v2_client.dsp_wallet_transfer_logs(
        jwt_token=jwt_token,
        csc_id=csc_id,
        status=status,
        utr=utr,
        from_date=from_date,
        to_date=to_date,
        rpp=rpp,
        cp=cp,
    )


@tool(
    name="adminGetDspWalletTransferDetails",
    description="Full DSP wallet transfer record for one transaction ID.",
    roles=ADMIN_ONLY,
    cacheable=True,
    ttl=30,
    domain="admin",
    source=SOURCE_GATEWAY_V2,
    endpoint="GET /v2/admin/dsp-wallet-transfer/{txnId}",
    examples=["DSP wallet transfer detail for txn DSP123456"],
)
async def admin_get_dsp_wallet_transfer_details(txn_id: str, jwt_token: str = None):
    return await admin_v2_client.dsp_wallet_transfer_details(txn_id, jwt_token)


@tool(
    name="adminGetDspDailySettlement",
    description="DSP daily settlement listing — per-day settled totals and status.",
    roles=ADMIN_ONLY,
    cacheable=True,
    ttl=120,
    domain="admin",
    source=SOURCE_GATEWAY_V2,
    endpoint="POST /v2/admin/dsp-wallet-transfer/daily-settlement",
    examples=["DSP daily settlement for yesterday"],
)
async def admin_get_dsp_daily_settlement(
    csc_id: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    rpp: int = 10,
    cp: int = 1,
    jwt_token: str = None,
):
    return await admin_v2_client.dsp_daily_settlement(
        jwt_token=jwt_token, csc_id=csc_id, from_date=from_date, to_date=to_date, rpp=rpp, cp=cp
    )
