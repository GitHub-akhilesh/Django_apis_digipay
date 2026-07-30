"""
Read-only clients for the remaining gateway controllers, each of which exposes
only one or two chat-relevant read endpoints:

    OperatorController              /v2/operator/list/{cscId}
    DeviceGatewayController         /v2/device/list
    ServiceCatalogGatewayController /v2/services/catalogs, /master-list
    AnalyticsController             /api/v2/analytics
    PayOutController                /v2/payout/status/{txnId}
    DspTopUpController              /v2/dsptopup/status/{txnId}
    AuaAuthController               /v2/aua/status/{txnId}
    UPIController                   /v1/upi/vpa/suggestion
    UserController                  /v2/user/publickey
    ExternalClientController        /v2/api/client/vle/balance
"""

from typing import Any, Optional

from gateway.v2.base import GatewayV2Client
from gateway.v2.filters import build_filter, require_csc_id, require_txn_id


class OperatorV2Client:
    SERVICE = "operator"

    async def list_operators(self, csc_id: str, jwt_token: Optional[str] = None) -> Any:
        csc_id = require_csc_id(csc_id)
        return await GatewayV2Client.call(
            method="GET",
            path=f"{GatewayV2Client.prefix(self.SERVICE)}/list/{csc_id}",
            service=self.SERVICE,
            operation="listOperators",
            csc_id=csc_id,
            jwt_token=jwt_token,
        )


class DeviceV2Client:
    SERVICE = "device"

    async def list_devices(self, jwt_token: Optional[str] = None, **filters) -> Any:
        payload = build_filter(**filters)
        return await GatewayV2Client.call(
            method="POST",
            path=f"{GatewayV2Client.prefix(self.SERVICE)}/list",
            service=self.SERVICE,
            operation="listDevices",
            csc_id=payload.get("cscId"),
            json_data=payload,
            jwt_token=jwt_token,
        )


class ServiceCatalogV2Client:
    SERVICE = "services"

    async def catalogs(self, jwt_token: Optional[str] = None) -> Any:
        return await GatewayV2Client.call(
            method="GET",
            path=f"{GatewayV2Client.prefix(self.SERVICE)}/catalogs",
            service=self.SERVICE,
            operation="serviceCatalog",
            headers={"X-App-Name": "AI_PLATFORM"},
            jwt_token=jwt_token,
        )

    async def master_list(self, jwt_token: Optional[str] = None) -> Any:
        return await GatewayV2Client.call(
            method="GET",
            path=f"{GatewayV2Client.prefix(self.SERVICE)}/master-list",
            service=self.SERVICE,
            operation="masterServiceList",
            jwt_token=jwt_token,
        )


class AnalyticsV2Client:
    SERVICE = "analytics"

    async def analytics(self, jwt_token: Optional[str] = None, **filters) -> Any:
        payload = build_filter(**filters)
        return await GatewayV2Client.call(
            method="POST",
            path=f"{GatewayV2Client.prefix(self.SERVICE)}/analytics",
            service=self.SERVICE,
            operation="merchantAnalytics",
            csc_id=payload.get("cscId"),
            json_data=payload,
            jwt_token=jwt_token,
        )


class StatusV2Client:
    """Transaction status lookups. These are pure reads — they never re-drive a
    transaction; the initiating POST routes are excluded in gateway.v2.safety."""

    async def payout_status(self, txn_id: str, jwt_token: Optional[str] = None) -> Any:
        txn_id = require_txn_id(txn_id)
        return await GatewayV2Client.call(
            method="GET",
            path=f"{GatewayV2Client.prefix('payout')}/status/{txn_id}",
            service="payout",
            operation="payoutStatus",
            txn_id=txn_id,
            jwt_token=jwt_token,
        )

    async def dsp_topup_status(self, txn_id: str, jwt_token: Optional[str] = None) -> Any:
        txn_id = require_txn_id(txn_id)
        return await GatewayV2Client.call(
            method="GET",
            path=f"{GatewayV2Client.prefix('dsptopup')}/status/{txn_id}",
            service="dsptopup",
            operation="dspTopUpStatus",
            txn_id=txn_id,
            jwt_token=jwt_token,
        )

    async def aua_status(
        self, txn_id: str, category: Optional[str] = None, jwt_token: Optional[str] = None
    ) -> Any:
        txn_id = require_txn_id(txn_id)
        params = {"category": str(category).strip().upper()} if category else None
        return await GatewayV2Client.call(
            method="GET",
            path=f"{GatewayV2Client.prefix('aua')}/status/{txn_id}",
            service="aua",
            operation="auaAuthStatus",
            txn_id=txn_id,
            params=params,
            jwt_token=jwt_token,
        )


class UpiV2Client:
    SERVICE = "upi"

    async def vpa_suggestion(self, jwt_token: Optional[str] = None) -> Any:
        return await GatewayV2Client.call(
            method="GET",
            path=f"{GatewayV2Client.prefix(self.SERVICE)}/vpa/suggestion",
            service=self.SERVICE,
            operation="upiVpaSuggestion",
            jwt_token=jwt_token,
        )


class UserV2Client:
    SERVICE = "user"

    async def public_key(self, jwt_token: Optional[str] = None) -> Any:
        return await GatewayV2Client.call(
            method="GET",
            path=f"{GatewayV2Client.prefix(self.SERVICE)}/publickey",
            service=self.SERVICE,
            operation="userPublicKey",
            jwt_token=jwt_token,
        )

    async def my_profile(
        self,
        csc_id: str,
        owner_id: Optional[str] = None,
        role: Optional[str] = None,
        jwt_token: Optional[str] = None,
    ) -> Any:
        """
        The signed-in user's own profile, bank details and enabled services.

        mode is pinned to "sync" - the read-only path the DigiPay web app uses
        after login. Other modes participate in the login flow and are not used.
        """
        csc_id = require_csc_id(csc_id)
        payload = {"cscId": csc_id, "ownerId": owner_id or csc_id, "mode": "sync"}
        if role:
            payload["role"] = str(role).strip()

        return await GatewayV2Client.call(
            method="POST",
            path=f"{GatewayV2Client.prefix(self.SERVICE)}/check-profile",
            service=self.SERVICE,
            operation="myProfile",
            csc_id=csc_id,
            json_data=payload,
            jwt_token=jwt_token,
        )


class ExternalPartnerV2Client:
    SERVICE = "external_client"

    async def vle_balance(
        self, csc_id: str, client_id: Optional[str] = None, jwt_token: Optional[str] = None
    ) -> Any:
        csc_id = require_csc_id(csc_id)
        payload = {"cscId": csc_id}
        if client_id:
            payload["clientId"] = str(client_id).strip()
        return await GatewayV2Client.call(
            method="POST",
            path=f"{GatewayV2Client.prefix(self.SERVICE)}/vle/balance",
            service=self.SERVICE,
            operation="externalVleBalance",
            csc_id=csc_id,
            json_data=payload,
            jwt_token=jwt_token,
        )


operator_v2_client = OperatorV2Client()
device_v2_client = DeviceV2Client()
service_catalog_v2_client = ServiceCatalogV2Client()
analytics_v2_client = AnalyticsV2Client()
status_v2_client = StatusV2Client()
upi_v2_client = UpiV2Client()
user_v2_client = UserV2Client()
external_partner_v2_client = ExternalPartnerV2Client()
