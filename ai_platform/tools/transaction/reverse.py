from tools.decorator import tool
from gateway.transaction_client import TransactionClient

transaction_client = TransactionClient()

@tool(
    name="reverseTransaction",
    description="Processes transaction reversal (restricted to support & admin)",
    roles=["ROLE_SUPPORT", "ROLE_ADMIN"],
    cacheable=False,
    read_only=False,
    requires_confirmation=True,
    domain="transaction"
)
async def reverse_transaction(txn_id: str, jwt_token: str = None):
    res = await transaction_client.reverse(txn_id.strip(), jwt_token)
    return f"Transaction {txn_id} successfully processed for reversal. Status: {res.status}"
