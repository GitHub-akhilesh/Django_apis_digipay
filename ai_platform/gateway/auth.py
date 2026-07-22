from core.config import settings

def get_internal_auth_headers() -> dict:
    """
    Constructs bypass and authentication headers for internal microservice calls.
    Includes X-Service-Name for auditing in Spring API Gateway logs.
    """
    return {
        "X-Service-Name": "AI_PLATFORM",
        "X-Internal-Client": "AI_PLATFORM",
        "X-Internal-Secret": getattr(settings, "INTERNAL_BYPASS_SECRET", "NPCI_INT3RNAL_Bypass_Secr3t_2026!")
    }
