from tools.decorator import tool
from gateway.notification_client import NotificationClient

notification_client = NotificationClient()

@tool(
    name="sendAlert",
    description="Dispatches push/SMS alert to merchant",
    roles=["ROLE_SUPPORT", "ROLE_ADMIN"]
)
async def send_alert(merchant_id: str, title: str = "Alert", body: str = "Notification", jwt_token: str = None):
    res = await notification_client.send_alert(merchant_id, title, body, jwt_token)
    return res.model_dump()
