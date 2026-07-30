"""
Read-only client for LedgerController (/v2/ledger).

/deposit, /withdrawal, /recovery and /transfer move money and are excluded in
gateway.v2.safety — only the balance, passbook and recovery-listing reads are
reachable from chat.
"""

import json
import logging
from typing import Any, Dict, Optional

from core.config import settings
from core.exceptions import GatewayException
from gateway.v2.base import GatewayV2Client
from gateway.v2.crypto import (
    decrypt_envelope,
    frontend_key_header,
    is_encrypted_envelope,
    verify_signature,
)
from gateway.v2.filters import build_filter, require_csc_id
from gateway.v2.platform_client import user_v2_client

logger = logging.getLogger("ai_platform.gateway.v2.ledger_client")

SERVICE = "ledger"


class LedgerV2Client:
    def _path(self, suffix: str) -> str:
        return f"{GatewayV2Client.prefix(SERVICE)}{suffix}"

    async def balance(self, csc_id: str, jwt_token: Optional[str] = None) -> Any:
        """
        Fetch the ledger balance and decrypt it.

        The gateway encrypts this response to the public key we advertise in
        X-Frontend-Key, so `resData` comes back as {payload, iv, key, signature}
        rather than as the balance itself. See gateway/v2/crypto.py for the format.
        """
        csc_id = require_csc_id(csc_id)

        res_data = await GatewayV2Client.call(
            method="GET",
            path=self._path("/balance"),
            service=SERVICE,
            operation="ledgerBalance",
            csc_id=csc_id,
            params={"cscId": csc_id},
            headers=frontend_key_header(),
            jwt_token=jwt_token,
        )

        # The gateway falls back to an unencrypted body on some error paths, so
        # only decrypt when an envelope is actually present.
        if not is_encrypted_envelope(res_data):
            return res_data

        if settings.GATEWAY_VERIFY_RESPONSE_SIGNATURE:
            await self._verify(res_data, jwt_token)

        plaintext = decrypt_envelope(res_data, operation="ledger balance")
        try:
            decoded = json.loads(plaintext)
            # Log the KEY NAMES only - never the values, which are financial data.
            # The message catalogue's field names are inferred from the Java source,
            # so this is how a mismatch is diagnosed instead of silently rendering
            # a balance with no amount in it.
            if isinstance(decoded, dict):
                logger.info(f"Ledger balance payload fields: {sorted(decoded.keys())}")
            return decoded
        except ValueError:
            # The gateway serialises resData with Gson; a non-JSON body means the
            # payload shape changed, so surface the text rather than discard it.
            logger.warning("Decrypted ledger balance was not JSON; returning raw text.")
            return plaintext

    async def _verify(self, envelope: Dict[str, Any], jwt_token: Optional[str]):
        """
        Verify the backend signature, fetching the backend public key from
        GET /v2/user/publickey. A verification failure is fatal; an inability to
        obtain the key is not — it degrades to unverified decryption with a warning,
        so a public-key endpoint outage does not take balance lookups down.
        """
        try:
            backend_key = await user_v2_client.public_key(jwt_token)
        except Exception as e:
            logger.warning(
                f"Could not fetch the backend public key to verify the balance response: {e}. "
                "Proceeding without signature verification."
            )
            return

        # resData is the base64 key string itself; tolerate a wrapped object too.
        if isinstance(backend_key, dict):
            backend_key = (
                backend_key.get("publicKey")
                or backend_key.get("resData")
                or backend_key.get("key")
            )
        if not isinstance(backend_key, str) or not backend_key.strip():
            logger.warning(
                "The backend public key endpoint returned no usable key; "
                "proceeding without signature verification."
            )
            return

        if verify_signature(envelope, backend_key.strip()):
            logger.debug("Backend signature verified on the ledger balance response.")

    async def passbook(self, jwt_token: Optional[str] = None, **filters) -> Any:
        payload = build_filter(require_csc=True, **filters)
        return await GatewayV2Client.call(
            method="POST",
            path=self._path("/passbook"),
            service=SERVICE,
            operation="ledgerPassbook",
            csc_id=payload.get("cscId"),
            json_data=payload,
            jwt_token=jwt_token,
        )

    async def recovery_list(self, jwt_token: Optional[str] = None, **filters) -> Any:
        payload = build_filter(**filters)
        return await GatewayV2Client.call(
            method="POST",
            path=self._path("/recovery/list"),
            service=SERVICE,
            operation="ledgerRecoveryList",
            csc_id=payload.get("cscId"),
            json_data=payload,
            jwt_token=jwt_token,
        )


ledger_v2_client = LedgerV2Client()
