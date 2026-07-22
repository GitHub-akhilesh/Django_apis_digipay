from tools.decorator import tool

@tool(
    name="lookupIFSC",
    description="Queries bank branch details for an IFSC code",
    roles=["ROLE_USER", "ROLE_MERCHANT", "ROLE_SUPPORT", "ROLE_ADMIN"],
    cacheable=True,
    ttl=3600
)
async def lookup_ifsc(ifsc_code: str, jwt_token: str = None):
    return {
        "ifsc": ifsc_code.upper(),
        "bank": "State Bank of India",
        "branch": "Main Branch",
        "city": "New Delhi",
        "state": "Delhi",
        "neft": True,
        "imps": True,
        "rtgs": True
    }
