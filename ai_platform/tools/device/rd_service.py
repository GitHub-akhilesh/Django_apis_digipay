from tools.decorator import tool

@tool(
    name="getRDDeviceStatus",
    description="Queries UIDAI Face RD & Aadhaar biometric device registration status",
    roles=["ROLE_USER", "ROLE_MERCHANT", "ROLE_SUPPORT", "ROLE_ADMIN"],
    cacheable=True,
    ttl=120
)
async def get_rd_device_status(merchant_id: str, jwt_token: str = None):
    return {
        "merchantId": merchant_id,
        "deviceModel": "Mantra MFS100",
        "rdServiceVersion": "v2.1",
        "status": "READY_ACTIVE",
        "registeredOn": "2026-01-15T09:00:00Z"
    }
