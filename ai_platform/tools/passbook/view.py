from tools.decorator import tool
from gateway.passbook_client import PassbookClient

passbook_client = PassbookClient()

@tool(
    name="getPassbook",
    description="Fetches passbook entries for a merchant",
    roles=["ROLE_USER", "ROLE_MERCHANT", "ROLE_SUPPORT", "ROLE_ADMIN"],
    cacheable=True
)
async def get_passbook(merchant_id: str, jwt_token: str = None):
    res = await passbook_client.get_passbook(merchant_id, jwt_token)
    return res.model_dump()
