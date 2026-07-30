"""Read-only client for TxnLogController (/v2/txn)."""

from typing import Any, Optional

from gateway.v2.base import GatewayV2Client
from gateway.v2.filters import build_filter

SERVICE = "txn"


class TxnLogV2Client:
    def _path(self, suffix: str) -> str:
        return f"{GatewayV2Client.prefix(SERVICE)}{suffix}"

    async def logs(self, jwt_token: Optional[str] = None, **filters) -> Any:
        """
        Paginated transaction log search. The gateway enforces cscId ownership
        via SecurityGuard.validateCscAccess, so cscId is mandatory here.
        """
        payload = build_filter(require_csc=True, **filters)
        return await GatewayV2Client.call(
            method="POST",
            path=self._path("/logs"),
            service=SERVICE,
            operation="txnLogs",
            csc_id=payload.get("cscId"),
            json_data=payload,
            jwt_token=jwt_token,
        )

    async def response(
        self,
        ref_no: str,
        txn_type: str,
        csc_id: Optional[str] = None,
        pc: int = 1,
        jwt_token: Optional[str] = None,
    ) -> Any:
        params = {
            "refNo": str(ref_no).strip(),
            "type": str(txn_type).strip().upper(),
            "pc": int(pc),
        }
        if csc_id:
            params["cscId"] = str(csc_id).strip()
        return await GatewayV2Client.call(
            method="GET",
            path=self._path("/response"),
            service=SERVICE,
            operation="txnLogResponse",
            csc_id=csc_id,
            txn_id=ref_no,
            params=params,
            jwt_token=jwt_token,
        )


txn_log_v2_client = TxnLogV2Client()
