from tools.decorator import tool
from gateway.ledger_client import LedgerClient

ledger_client = LedgerClient()

@tool(
    name="getLedgerStatement",
    description="Fetches ledger statement entries for a merchant",
    roles=["ROLE_USER", "ROLE_MERCHANT", "ROLE_SUPPORT", "ROLE_ADMIN"],
    cacheable=True
)
async def get_ledger_statement(merchant_id: str, jwt_token: str = None):
    res = await ledger_client.get_statement(merchant_id, jwt_token=jwt_token)
    return res.model_dump()
