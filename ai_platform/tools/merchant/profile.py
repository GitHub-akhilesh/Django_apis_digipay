from tools.decorator import tool
from gateway.merchant_client import MerchantClient

merchant_client = MerchantClient()

@tool(
    name="getMerchantProfile",
    description="Fetches merchant profile info",
    roles=["ROLE_USER", "ROLE_MERCHANT", "ROLE_SUPPORT", "ROLE_ADMIN"],
    cacheable=True
)
async def get_merchant_profile(merchant_id: str, jwt_token: str = None):
    res = await merchant_client.get_profile(merchant_id, jwt_token)
    return res.model_dump()
