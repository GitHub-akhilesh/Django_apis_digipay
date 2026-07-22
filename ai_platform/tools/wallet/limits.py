from tools.decorator import tool
from gateway.wallet_client import WalletClient

wallet_client = WalletClient()

@tool(
    name="getLimits",
    description="Fetches daily limits for a merchant wallet",
    roles=["ROLE_USER", "ROLE_MERCHANT", "ROLE_SUPPORT", "ROLE_ADMIN"],
    cacheable=True,
    ttl=60
)
async def get_wallet_limits(merchant_id: str, jwt_token: str = None):
    res = await wallet_client.get_limits(merchant_id, jwt_token)
    return res.model_dump()
