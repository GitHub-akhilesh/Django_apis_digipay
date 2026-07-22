from tools.decorator import tool
from gateway.wallet_client import WalletClient

wallet_client = WalletClient()

@tool(
    name="getWalletBalance",
    description="Fetches current wallet balance for a merchant",
    roles=["ROLE_USER", "ROLE_MERCHANT", "ROLE_SUPPORT", "ROLE_ADMIN"],
    cacheable=True,
    ttl=30
)
async def get_wallet_balance(merchant_id: str, jwt_token: str = None):
    res = await wallet_client.get_balance(merchant_id, jwt_token)
    return res.model_dump()
