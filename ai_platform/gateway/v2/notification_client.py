"""
Read-only client for NotificationController (/v2/notification).

/create and /delete are excluded in gateway.v2.safety — the assistant reads
notifications, it never authors or removes them.
"""

from typing import Any, Optional

from gateway.v2.base import GatewayV2Client
from gateway.v2.filters import build_filter

SERVICE = "notification"


class NotificationV2Client:
    def _path(self, suffix: str) -> str:
        return f"{GatewayV2Client.prefix(SERVICE)}{suffix}"

    async def fetch(self, jwt_token: Optional[str] = None, **filters) -> Any:
        payload = build_filter(**filters)
        return await GatewayV2Client.call(
            method="POST",
            path=self._path("/fetch"),
            service=SERVICE,
            operation="fetchNotifications",
            csc_id=payload.get("cscId"),
            json_data=payload,
            jwt_token=jwt_token,
        )

    async def fetch_login(self, jwt_token: Optional[str] = None, **filters) -> Any:
        payload = build_filter(**filters)
        return await GatewayV2Client.call(
            method="POST",
            path=self._path("/fetch/login"),
            service=SERVICE,
            operation="fetchLoginNotifications",
            csc_id=payload.get("cscId"),
            json_data=payload,
            jwt_token=jwt_token,
        )


notification_v2_client = NotificationV2Client()
