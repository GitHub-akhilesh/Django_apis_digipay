"""
Chat tools for transaction history and AePS enquiry records.

Backed by TxnLogController (/v2/txn) and the read-only routes of AepsController
(/v2/aeps). Nothing here can start a transaction: the AePS POST routes that hit
the switch are excluded in gateway.v2.safety.
"""

from typing import Optional

from gateway.v2.aeps_client import aeps_v2_client
from gateway.v2.txn_client import txn_log_v2_client
from tools.decorator import SOURCE_GATEWAY_V2, tool

ALL_ROLES = ["ROLE_USER", "ROLE_MERCHANT", "ROLE_SUPPORT", "ROLE_ADMIN"]


@tool(
    name="getTxnLogs",
    description=(
        "Search a merchant's DigiPay transaction history. Filter by service type "
        "(AEPS_CASH_WITHDRAWAL, AEPS_BALANCE_ENQUIRY, PAYOUT, DSP_TOPUP, VATM_WITHDRAWAL, "
        "UPI_CASH_WITHDRAWAL and similar), status, RRN, UTR, transaction ID and date range. "
        "Use this for 'show my transactions', 'did my payment go through', 'failed transactions'."
    ),
    roles=ALL_ROLES,
    cacheable=True,
    ttl=30,
    domain="transaction",
    source=SOURCE_GATEWAY_V2,
    endpoint="POST /v2/txn/logs",
    examples=[
        "show my transactions from last week",
        "list my failed AePS withdrawals",
        "find the transaction with RRN 512345678901",
    ],
)
async def get_txn_logs(
    csc_id: str,
    # `type` is REQUIRED by the gateway even though FillterBO does not mark it so:
    # omitting it makes /v2/txn/logs answer 200 with a non-OK envelope and no
    # message, which surfaced as "the gateway rejected the request" with nothing
    # to act on. The DigiPay web app always sends it (see Logs.jsx). "ALL" is used
    # when the user did not name a service, matching the portal's default view.
    type: str = "ALL",
    txn_type: Optional[str] = None,
    status: Optional[str] = None,
    txn_id: Optional[str] = None,
    rrn: Optional[str] = None,
    utr: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    rpp: int = 10,
    cp: int = 1,
    jwt_token: str = None,
):
    return await txn_log_v2_client.logs(
        jwt_token=jwt_token,
        csc_id=csc_id,
        type=type,
        txn_type=txn_type,
        status=status,
        txn_id=txn_id,
        rrn=rrn,
        utr=utr,
        from_date=from_date,
        to_date=to_date,
        rpp=rpp,
        cp=cp,
    )


@tool(
    name="getTxnResponse",
    description=(
        "Fetch the recorded switch/bank response for one transaction reference number. "
        "Requires the service category. Use this to explain WHY a transaction failed."
    ),
    roles=ALL_ROLES,
    cacheable=True,
    ttl=30,
    domain="transaction",
    source=SOURCE_GATEWAY_V2,
    endpoint="GET /v2/txn/response",
    examples=["why did transaction 512345678901 fail", "show the bank response for my withdrawal"],
)
async def get_txn_response(
    ref_no: str,
    type: str,
    csc_id: Optional[str] = None,
    pc: int = 1,
    jwt_token: str = None,
):
    return await txn_log_v2_client.response(
        ref_no=ref_no, txn_type=type, csc_id=csc_id, pc=pc, jwt_token=jwt_token
    )


@tool(
    name="getAepsBalanceEnquiryResponse",
    description=(
        "Fetch the stored result of an AePS balance enquiry that already ran, by its "
        "reference number. This reads a past record; it does not run a new enquiry."
    ),
    roles=ALL_ROLES,
    cacheable=True,
    ttl=30,
    domain="aeps",
    source=SOURCE_GATEWAY_V2,
    endpoint="GET /v2/aeps/balance-enquiry-response",
    examples=["what was the result of AePS enquiry ref 512345678901"],
)
async def get_aeps_balance_enquiry_response(ref_no: str, jwt_token: str = None):
    return await aeps_v2_client.balance_enquiry_response(ref_no, jwt_token)


@tool(
    name="getAepsBalanceEnquiryList",
    description="Paginated history of AePS balance enquiries for a CSC ID, filterable by date range and bank IIN.",
    roles=ALL_ROLES,
    cacheable=True,
    ttl=30,
    domain="aeps",
    source=SOURCE_GATEWAY_V2,
    endpoint="POST /v2/aeps/balance-enquiry-list",
    examples=["my AePS balance enquiries this month"],
)
async def get_aeps_balance_enquiry_list(
    csc_id: Optional[str] = None,
    owner_id: Optional[str] = None,
    bank_iin: Optional[str] = None,
    status: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    rpp: int = 10,
    cp: int = 1,
    jwt_token: str = None,
):
    return await aeps_v2_client.balance_enquiry_list(
        jwt_token=jwt_token,
        csc_id=csc_id,
        owner_id=owner_id,
        bank_iin=bank_iin,
        status=status,
        from_date=from_date,
        to_date=to_date,
        rpp=rpp,
        cp=cp,
    )


@tool(
    name="getAepsBalanceEnquiryDetails",
    description="Full detail of one AePS balance enquiry, located by transaction ID or RRN.",
    roles=ALL_ROLES,
    cacheable=True,
    ttl=30,
    domain="aeps",
    source=SOURCE_GATEWAY_V2,
    endpoint="POST /v2/aeps/balance-enquiry-details",
    examples=["details of AePS enquiry txn AEP12345"],
)
async def get_aeps_balance_enquiry_details(
    csc_id: Optional[str] = None,
    txn_id: Optional[str] = None,
    rrn: Optional[str] = None,
    jwt_token: str = None,
):
    return await aeps_v2_client.balance_enquiry_details(
        jwt_token=jwt_token, csc_id=csc_id, txn_id=txn_id, rrn=rrn
    )


@tool(
    name="getAepsLogs",
    description=(
        "Paginated AePS transaction logs (withdrawals, deposits, mini statements, enquiries). "
        "Filter by CSC ID, transaction type, status, bank IIN and date range."
    ),
    roles=ALL_ROLES,
    cacheable=True,
    ttl=30,
    domain="aeps",
    source=SOURCE_GATEWAY_V2,
    endpoint="POST /v2/aeps/logs",
    examples=["my AePS transactions today", "AePS cash withdrawals last week"],
)
async def get_aeps_logs(
    csc_id: Optional[str] = None,
    owner_id: Optional[str] = None,
    txn_type: Optional[str] = None,
    status: Optional[str] = None,
    bank_iin: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    rpp: int = 10,
    cp: int = 1,
    jwt_token: str = None,
):
    return await aeps_v2_client.logs(
        jwt_token=jwt_token,
        csc_id=csc_id,
        owner_id=owner_id,
        txn_type=txn_type,
        status=status,
        bank_iin=bank_iin,
        from_date=from_date,
        to_date=to_date,
        rpp=rpp,
        cp=cp,
    )


@tool(
    name="getAepsLogDetails",
    description="Full detail of one AePS transaction, located by transaction ID or RRN.",
    roles=ALL_ROLES,
    cacheable=True,
    ttl=30,
    domain="aeps",
    source=SOURCE_GATEWAY_V2,
    endpoint="POST /v2/aeps/log-details",
    examples=["details of AePS withdrawal AEP12345"],
)
async def get_aeps_log_details(
    csc_id: Optional[str] = None,
    txn_id: Optional[str] = None,
    rrn: Optional[str] = None,
    jwt_token: str = None,
):
    return await aeps_v2_client.log_details(
        jwt_token=jwt_token, csc_id=csc_id, txn_id=txn_id, rrn=rrn
    )
