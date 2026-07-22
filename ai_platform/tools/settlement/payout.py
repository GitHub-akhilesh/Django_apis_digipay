from tools.decorator import tool

@tool(
    name="getPayoutStatus",
    description="Queries IMPS/NEFT payout settlement status for a merchant",
    roles=["ROLE_USER", "ROLE_MERCHANT", "ROLE_SUPPORT", "ROLE_ADMIN"],
    cacheable=True,
    ttl=30
)
async def get_payout_status(merchant_id: str, jwt_token: str = None):
    return {
        "merchantId": merchant_id,
        "settlementStatus": "PROCESSED_SUCCESS",
        "mode": "IMPS",
        "utr": "IMPS2026072188921",
        "amount": 4560.50
    }
