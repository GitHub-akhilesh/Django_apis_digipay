from tools.decorator import tool

@tool(
    name="validateVPA",
    description="Validates UPI Virtual Payment Address (VPA)",
    roles=["ROLE_USER", "ROLE_MERCHANT", "ROLE_SUPPORT", "ROLE_ADMIN"],
    cacheable=True,
    ttl=60
)
async def validate_vpa(vpa: str, jwt_token: str = None):
    is_valid = "@" in vpa and len(vpa) > 5
    return {
        "vpa": vpa,
        "valid": is_valid,
        "accountHolder": "CSC Merchant VLE" if is_valid else "Unknown"
    }
