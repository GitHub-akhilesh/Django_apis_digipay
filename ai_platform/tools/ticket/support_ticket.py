from tools.decorator import tool

@tool(
    name="raiseTicket",
    description="Creates a support ticket for a merchant issue",
    roles=["ROLE_USER", "ROLE_MERCHANT", "ROLE_SUPPORT", "ROLE_ADMIN"]
)
async def raise_ticket(merchant_id: str, category: str = "General", details: str = "", jwt_token: str = None):
    return {
        "ticketId": "TCK-881923",
        "merchantId": merchant_id,
        "category": category,
        "details": details,
        "status": "OPEN",
        "createdAt": "2026-07-21T11:00:00Z"
    }

@tool(
    name="getTicketStatus",
    description="Fetches status of a support ticket by ID",
    roles=["ROLE_USER", "ROLE_MERCHANT", "ROLE_SUPPORT", "ROLE_ADMIN"],
    cacheable=True
)
async def get_ticket_status(ticket_id: str, jwt_token: str = None):
    return {
        "ticketId": ticket_id,
        "status": "IN_PROGRESS",
        "assignedAgent": "Level-2 Support Team",
        "lastUpdated": "2026-07-21T11:30:00Z"
    }
