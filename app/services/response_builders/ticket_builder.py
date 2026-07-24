from typing import Dict, Any

class TicketResponseBuilder:
    @staticmethod
    def format_raise_ticket(res: Dict[str, Any]) -> str:
        return f"I have raised a support ticket for your issue. Ticket ID: {res['ticketId']} (Category: {res['category']}). Our Level-2 team will investigate immediately."

    @staticmethod
    def format_close_ticket(res: Dict[str, Any]) -> str:
        return f"Ticket {res['ticketId']} has been successfully CLOSED on {res.get('closedAt')}."
