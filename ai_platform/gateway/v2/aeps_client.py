"""
Read-only client for AepsController (/v2/aeps).

Only the enquiry/history routes are reachable. The POST routes that drive a live
biometric transaction at the switch (/balance-enquiry, /cash-withdrawal,
/cash-deposit, /mini-statement, /reqotp) are excluded in gateway.v2.safety and
cannot be called from here.
"""

from typing import Any, Optional

from gateway.v2.base import GatewayV2Client
from gateway.v2.filters import build_filter

SERVICE = "aeps"


class AepsV2Client:
    def _path(self, suffix: str) -> str:
        return f"{GatewayV2Client.prefix(SERVICE)}{suffix}"

    async def balance_enquiry_response(self, ref_no: str, jwt_token: Optional[str] = None) -> Any:
        return await GatewayV2Client.call(
            method="GET",
            path=self._path("/balance-enquiry-response"),
            service=SERVICE,
            operation="aepsBalanceEnquiryResponse",
            txn_id=ref_no,
            params={"refNo": str(ref_no).strip()},
            jwt_token=jwt_token,
        )

    async def balance_enquiry_list(self, jwt_token: Optional[str] = None, **filters) -> Any:
        payload = build_filter(**filters)
        return await GatewayV2Client.call(
            method="POST",
            path=self._path("/balance-enquiry-list"),
            service=SERVICE,
            operation="aepsBalanceEnquiryList",
            csc_id=payload.get("cscId"),
            json_data=payload,
            jwt_token=jwt_token,
        )

    async def balance_enquiry_details(self, jwt_token: Optional[str] = None, **filters) -> Any:
        payload = build_filter(**filters)
        return await GatewayV2Client.call(
            method="POST",
            path=self._path("/balance-enquiry-details"),
            service=SERVICE,
            operation="aepsBalanceEnquiryDetails",
            csc_id=payload.get("cscId"),
            txn_id=payload.get("txnId"),
            json_data=payload,
            jwt_token=jwt_token,
        )

    async def logs(self, jwt_token: Optional[str] = None, **filters) -> Any:
        payload = build_filter(**filters)
        return await GatewayV2Client.call(
            method="POST",
            path=self._path("/logs"),
            service=SERVICE,
            operation="aepsLogs",
            csc_id=payload.get("cscId"),
            json_data=payload,
            jwt_token=jwt_token,
        )

    async def log_details(self, jwt_token: Optional[str] = None, **filters) -> Any:
        payload = build_filter(**filters)
        return await GatewayV2Client.call(
            method="POST",
            path=self._path("/log-details"),
            service=SERVICE,
            operation="aepsLogDetails",
            csc_id=payload.get("cscId"),
            txn_id=payload.get("txnId"),
            json_data=payload,
            jwt_token=jwt_token,
        )


aeps_v2_client = AepsV2Client()
