from tools.decorator import tool
from gateway.transaction_client import TransactionClient

transaction_client = TransactionClient()

@tool(
    name="getTransaction",
    description="Fetches details for a transaction by ID",
    roles=["ROLE_USER", "ROLE_MERCHANT", "ROLE_SUPPORT", "ROLE_ADMIN"],
    cacheable=True
)
async def get_transaction(txn_id: str, jwt_token: str = None):
    res = await transaction_client.get_transaction(txn_id, jwt_token)
    return res.model_dump()
