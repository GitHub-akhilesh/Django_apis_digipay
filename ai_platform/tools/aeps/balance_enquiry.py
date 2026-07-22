from tools.decorator import tool
from gateway.aeps_client import AEPSClient

aeps_client = AEPSClient()

@tool(
    name="balanceEnquiry",
    description="Performs AEPS biometric balance enquiry",
    roles=["ROLE_USER", "ROLE_MERCHANT", "ROLE_SUPPORT", "ROLE_ADMIN"],
    cacheable=True
)
async def balance_enquiry(merchant_id: str, jwt_token: str = None):
    res = await aeps_client.balance_enquiry(merchant_id, jwt_token)
    return res.model_dump()
