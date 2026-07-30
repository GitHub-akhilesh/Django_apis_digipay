"""
Read-only chat tools for the legacy DigiPay API service (app/main.py).

Endpoint mapping (URLs unchanged — the legacy service is called as-is):

    POST /api/v1/txn-logs        -> getLegacyTxnLogs
    POST /api/v1/passbook        -> getLegacyPassbook
    POST /api/v1/wallet_balance  -> getLegacyWalletBalance

/auth/token, /daywise_report (zip download) and /agent/* are excluded in
gateway.legacy_v1.client.EXCLUDED_ENDPOINTS.
"""

from typing import Optional

from core.exceptions import ValidationException
from gateway.legacy_v1.client import legacy_v1_client
from tools.decorator import SOURCE_LEGACY_API, tool

ALL_ROLES = ["ROLE_USER", "ROLE_MERCHANT", "ROLE_SUPPORT", "ROLE_ADMIN"]


def _require(value: Optional[str], field: str) -> str:
    if not value or not str(value).strip():
        raise ValidationException(f"'{field}' is required for the legacy DigiPay API.")
    return str(value).strip()


@tool(
    name="getLegacyTxnLogs",
    description=(
        "Transaction logs from the legacy DigiPay API service. Requires a service type "
        "(for example AEPS_CASH_WITHDRAWAL) and a dd-MM-yyyy date range. Use this when the "
        "user asks about older or archived transactions held in the legacy system."
    ),
    roles=ALL_ROLES,
    cacheable=True,
    ttl=30,
    domain="legacy",
    source=SOURCE_LEGACY_API,
    endpoint="POST /api/v1/txn-logs",
    examples=[
        "show my legacy transaction logs for July",
        "check the old system for my AePS withdrawals",
    ],
)
async def get_legacy_txn_logs(
    csc_id: str,
    type: str,
    from_date: str,
    to_date: str,
    search: str = "",
    rpp: int = 10,
    cp: int = 1,
    jwt_token: str = None,
):
    return await legacy_v1_client.call(
        method="POST",
        path="/txn-logs",
        operation="legacyTxnLogs",
        json_data={
            "cscId": _require(csc_id, "cscId"),
            "type": _require(type, "type"),
            "fromDate": _require(from_date, "fromDate"),
            "toDate": _require(to_date, "toDate"),
            "search": search or "",
            "rpp": min(int(rpp), 50),
            "cp": int(cp),
        },
        jwt_token=jwt_token,
    )


@tool(
    name="getLegacyPassbook",
    description=(
        "Passbook entries from the legacy DigiPay API service, for a CSC ID over a "
        "dd-MM-yyyy date range. Use this for older passbook data held in the legacy system."
    ),
    roles=ALL_ROLES,
    cacheable=True,
    ttl=30,
    domain="legacy",
    source=SOURCE_LEGACY_API,
    endpoint="POST /api/v1/passbook",
    examples=["show my legacy passbook for June", "old system passbook entries"],
)
async def get_legacy_passbook(
    csc_id: str,
    from_date: str,
    to_date: str,
    search: str = "",
    rpp: int = 10,
    cp: int = 1,
    jwt_token: str = None,
):
    return await legacy_v1_client.call(
        method="POST",
        path="/passbook",
        operation="legacyPassbook",
        json_data={
            "cscId": _require(csc_id, "cscId"),
            "fromDate": _require(from_date, "fromDate"),
            "toDate": _require(to_date, "toDate"),
            "search": search or "",
            "rpp": min(int(rpp), 50),
            "cp": int(cp),
        },
        jwt_token=jwt_token,
    )


@tool(
    name="getLegacyWalletBalance",
    description=(
        "Wallet balance from the legacy DigiPay API service for a CSC ID. Use this when the "
        "user asks specifically about their old or legacy DigiPay wallet balance."
    ),
    roles=ALL_ROLES,
    cacheable=True,
    ttl=15,
    domain="legacy",
    source=SOURCE_LEGACY_API,
    endpoint="POST /api/v1/wallet_balance",
    examples=["what is my legacy wallet balance", "old DigiPay balance"],
)
async def get_legacy_wallet_balance(csc_id: str, jwt_token: str = None):
    # The legacy endpoint takes a list and returns a cscId -> balance map.
    result = await legacy_v1_client.call(
        method="POST",
        path="/wallet_balance",
        operation="legacyWalletBalance",
        json_data={"csc_ids": [_require(csc_id, "cscId")]},
        jwt_token=jwt_token,
    )

    # The endpoint answers {cscId: balance}. Flatten the single entry so the
    # message catalogue can label it, and treat the reference implementation's
    # "Wallet balance not available" sentinel as no data rather than rendering it
    # in the Balance field, where it would read as a corrupted amount.
    UNAVAILABLE = "wallet balance not available"

    if isinstance(result, dict):
        entry = result.get(csc_id)
        if entry is None and len(result) == 1:
            csc_id, entry = next(iter(result.items()))
        if entry is None:
            return {}
        if str(entry).strip().lower() == UNAVAILABLE:
            return {}
        return {"cscId": csc_id, "balance": entry}

    return result
