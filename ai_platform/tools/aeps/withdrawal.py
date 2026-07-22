from tools.decorator import tool
from gateway.aeps_client import AEPSClient

aeps_client = AEPSClient()

@tool(
    name="cashWithdrawalStatus",
    description="Queries AEPS cash withdrawal transaction status",
    roles=["ROLE_USER", "ROLE_MERCHANT", "ROLE_SUPPORT", "ROLE_ADMIN"],
    cacheable=True
)
async def cash_withdrawal_status(txn_id: str, jwt_token: str = None):
    res = await aeps_client.cash_withdrawal(txn_id, 0.0, jwt_token)
    return res.model_dump()
