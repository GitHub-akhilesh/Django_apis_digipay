from tools.decorator import tool
from gateway.merchant_client import MerchantClient

merchant_client = MerchantClient()

@tool(
    name="getMerchantStatus",
    description="Fetches merchant KYC & active status",
    roles=["ROLE_USER", "ROLE_MERCHANT", "ROLE_SUPPORT", "ROLE_ADMIN"],
    cacheable=True
)
async def get_merchant_status(merchant_id: str, jwt_token: str = None):
    res = await merchant_client.get_status(merchant_id, jwt_token)
    return res.model_dump()
