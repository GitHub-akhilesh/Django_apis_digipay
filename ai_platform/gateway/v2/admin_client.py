"""Read-only client for AdminController (/v2/admin)."""

from typing import Any, Dict, Optional

from gateway.v2.base import GatewayV2Client
from gateway.v2.filters import build_filter, require_csc_id, require_txn_id

SERVICE = "admin"


class AdminV2Client:
    def _path(self, suffix: str) -> str:
        return f"{GatewayV2Client.prefix(SERVICE)}{suffix}"

    async def _post_filter(
        self, suffix: str, operation: str, payload: Dict[str, Any], jwt_token: Optional[str] = None
    ) -> Any:
        return await GatewayV2Client.call(
            method="POST",
            path=self._path(suffix),
            service=SERVICE,
            operation=operation,
            csc_id=payload.get("cscId"),
            txn_id=payload.get("txnId"),
            json_data=payload,
            jwt_token=jwt_token,
        )

    async def user_list(self, jwt_token: Optional[str] = None, **filters) -> Any:
        return await self._post_filter("/user/list", "adminUserList", build_filter(**filters), jwt_token)

    async def daily_txn_report(self, jwt_token: Optional[str] = None, **filters) -> Any:
        return await self._post_filter("/dailytxnreport", "adminDailyTxnReport", build_filter(**filters), jwt_token)

    async def report(self, jwt_token: Optional[str] = None, **filters) -> Any:
        return await self._post_filter("/report", "adminReport", build_filter(**filters), jwt_token)

    async def profile_operator_list(self, csc_id: str, jwt_token: Optional[str] = None) -> Any:
        # LoginBO body — cscId is the discriminator the gateway validates.
        return await GatewayV2Client.call(
            method="POST",
            path=self._path("/profileDetails/orpList"),
            service=SERVICE,
            operation="adminProfileOperatorList",
            csc_id=require_csc_id(csc_id),
            json_data={"cscId": require_csc_id(csc_id)},
            jwt_token=jwt_token,
        )

    async def txn_details(self, ref_no: str, txn_type: str, jwt_token: Optional[str] = None) -> Any:
        return await GatewayV2Client.call(
            method="GET",
            path=self._path("/txn-details"),
            service=SERVICE,
            operation="adminTxnDetails",
            txn_id=ref_no,
            params={"refNo": str(ref_no).strip(), "type": str(txn_type).strip().upper()},
            jwt_token=jwt_token,
        )

    async def user_details(self, csc_id: str, jwt_token: Optional[str] = None) -> Any:
        csc_id = require_csc_id(csc_id)
        return await GatewayV2Client.call(
            method="GET",
            path=self._path(f"/details/{csc_id}"),
            service=SERVICE,
            operation="adminUserDetails",
            csc_id=csc_id,
            jwt_token=jwt_token,
        )

    async def login_journey(self, jwt_token: Optional[str] = None, **filters) -> Any:
        return await self._post_filter("/user/login-journey", "adminLoginJourney", build_filter(**filters), jwt_token)

    async def block_history(self, jwt_token: Optional[str] = None, **filters) -> Any:
        return await self._post_filter("/user/block-history", "adminBlockHistory", build_filter(**filters), jwt_token)

    async def user_operators(self, jwt_token: Optional[str] = None, **filters) -> Any:
        return await self._post_filter("/user/operators", "adminUserOperators", build_filter(**filters), jwt_token)

    async def agent_auth_logs(self, jwt_token: Optional[str] = None, **filters) -> Any:
        return await self._post_filter("/user/agent-auth", "adminAgentAuthLogs", build_filter(**filters), jwt_token)

    async def service_history(self, jwt_token: Optional[str] = None, **filters) -> Any:
        return await self._post_filter("/service-history", "adminServiceHistory", build_filter(**filters), jwt_token)

    async def timeout_txn_list(self, jwt_token: Optional[str] = None, **filters) -> Any:
        return await self._post_filter("/timeout/list", "adminTimeoutTxnList", build_filter(**filters), jwt_token)

    async def service_status_schedules(self, jwt_token: Optional[str] = None, **filters) -> Any:
        """Planned service up/down windows. Read only: the schedule and cancel
        siblings on this controller mutate and are excluded in safety.py."""
        return await self._post_filter(
            "/service-status/schedule/list", "adminServiceStatusSchedules",
            build_filter(**filters), jwt_token
        )

    async def dsp_wallet_transfer_logs(self, jwt_token: Optional[str] = None, **filters) -> Any:
        return await self._post_filter(
            "/dsp-wallet-transfer/logs", "adminDspWalletTransferLogs", build_filter(**filters), jwt_token
        )

    async def dsp_wallet_transfer_details(self, txn_id: str, jwt_token: Optional[str] = None) -> Any:
        txn_id = require_txn_id(txn_id)
        return await GatewayV2Client.call(
            method="GET",
            path=self._path(f"/dsp-wallet-transfer/{txn_id}"),
            service=SERVICE,
            operation="adminDspWalletTransferDetails",
            txn_id=txn_id,
            jwt_token=jwt_token,
        )

    async def dsp_daily_settlement(self, jwt_token: Optional[str] = None, **filters) -> Any:
        return await self._post_filter(
            "/dsp-wallet-transfer/daily-settlement", "adminDspDailySettlement", build_filter(**filters), jwt_token
        )


admin_v2_client = AdminV2Client()
