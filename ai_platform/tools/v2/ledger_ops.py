"""
Chat tools for LedgerController (/v2/ledger) — balance and passbook reads.

The deposit, withdrawal, recovery and wallet-transfer routes on the same
controller move money and are excluded in gateway.v2.safety.
"""

from typing import Optional

from gateway.v2.ledger_client import ledger_v2_client
from tools.decorator import SOURCE_GATEWAY_V2, tool

ALL_ROLES = ["ROLE_USER", "ROLE_MERCHANT", "ROLE_SUPPORT", "ROLE_ADMIN"]


@tool(
    name="getLedgerBalanceV2",
    description=(
        "Current DigiPay ledger (wallet) balance for a 12-character CSC ID, read live "
        "from the ledger service. Use this for 'what is my balance', 'how much money do I have'."
    ),
    roles=ALL_ROLES,
    cacheable=True,
    ttl=15,
    domain="ledger",
    source=SOURCE_GATEWAY_V2,
    endpoint="GET /v2/ledger/balance",
    examples=["what is my ledger balance", "how much balance do I have left"],
)
async def get_ledger_balance_v2(csc_id: str, jwt_token: str = None):
    return await ledger_v2_client.balance(csc_id, jwt_token)


@tool(
    name="getLedgerPassbookV2",
    description=(
        "Ledger passbook entries (credits and debits with running balance) for a CSC ID. "
        "Filter by ledger transaction type, status and date range. Use this for "
        "'show my passbook', 'where did my money go', 'statement of account'."
    ),
    roles=ALL_ROLES,
    cacheable=True,
    ttl=30,
    domain="ledger",
    source=SOURCE_GATEWAY_V2,
    endpoint="POST /v2/ledger/passbook",
    examples=["show my passbook for this month", "list my ledger credits"],
)
async def get_ledger_passbook_v2(
    csc_id: str,
    lgr_txn_type: Optional[str] = None,
    status: Optional[str] = None,
    txn_id: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    rpp: int = 10,
    cp: int = 1,
    jwt_token: str = None,
):
    return await ledger_v2_client.passbook(
        jwt_token=jwt_token,
        csc_id=csc_id,
        lgr_txn_type=lgr_txn_type,
        status=status,
        txn_id=txn_id,
        from_date=from_date,
        to_date=to_date,
        rpp=rpp,
        cp=cp,
    )


@tool(
    name="getLedgerRecoveryList",
    description=(
        "List ledger recovery cases (amounts being recovered from VLE ledgers). "
        "Read-only listing; initiating a recovery is not available from chat."
    ),
    roles=["ROLE_ADMIN"],
    cacheable=True,
    ttl=60,
    domain="ledger",
    source=SOURCE_GATEWAY_V2,
    endpoint="POST /v2/ledger/recovery/list",
    examples=["show open ledger recovery cases"],
)
async def get_ledger_recovery_list(
    csc_id: Optional[str] = None,
    status: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    rpp: int = 10,
    cp: int = 1,
    jwt_token: str = None,
):
    return await ledger_v2_client.recovery_list(
        jwt_token=jwt_token,
        csc_id=csc_id,
        status=status,
        from_date=from_date,
        to_date=to_date,
        rpp=rpp,
        cp=cp,
    )
