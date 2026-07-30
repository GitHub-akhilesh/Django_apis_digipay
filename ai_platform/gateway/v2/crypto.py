"""
Hybrid-envelope decryption for gateway responses.

WHY THIS EXISTS
---------------
`GET /v2/ledger/balance` requires an `X-Frontend-Key` header. That header is NOT
a shared secret or an API key — it is the *caller's own* RSA public key, base64
X.509 SubjectPublicKeyInfo. `LedgerController` passes it to
`LedgerService.balanceEnquiry`, which calls `Crypto.encryptForFrontend` and
returns the balance encrypted to that key, so only the caller can read it.

So there is nothing to look up and paste into configuration. This platform has to
hold its own RSA keypair, advertise the public half, and decrypt the reply.

WIRE FORMAT (from com.digipay.common.utils.Crypto)
-------------------------------------------------
`resData` is a map of base64 strings:

    key         AES-256 key wrapped with RSA/ECB/OAEPWithSHA-256AndMGF1Padding
                (OAEP, SHA-256 digest AND SHA-256 MGF1, empty label)
    iv          12-byte GCM nonce
    payload     AES/GCM/NoPadding ciphertext with the 128-bit tag appended,
                which is the JCE convention and matches what AESGCM expects here
    signature   optional SHA256withRSA (RSASSA-PKCS1-v1_5) over the raw bytes
                encryptedPayload || encryptedAesKey, signed by the backend's
                private key from backend-keystore.p12

The backend public key needed to verify that signature is served at runtime by
`GET /v2/user/publickey` — exposed as the `getPlatformPublicKey` tool — so it is
fetched rather than copied into this repo.
"""

import base64
import binascii
import logging
import os
from typing import Any, Dict, Optional

from cryptography.exceptions import InvalidSignature, InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from core.config import settings
from core.exceptions import GatewayException

logger = logging.getLogger("ai_platform.gateway.v2.crypto")

GCM_IV_LENGTH = 12
GCM_TAG_LENGTH = 16

# Fields of the encrypted envelope returned in resData.
ENVELOPE_FIELDS = ("key", "iv", "payload")

# RSA/ECB/OAEPWithSHA-256AndMGF1Padding — note SHA-256 for BOTH the digest and
# MGF1. Java's default MGF1 would be SHA-1; this transform overrides it, and
# getting it wrong produces a decryption failure with no useful diagnostic.
OAEP_PADDING = padding.OAEP(
    mgf=padding.MGF1(algorithm=hashes.SHA256()),
    algorithm=hashes.SHA256(),
    label=None,
)


class ClientKeyPair:
    """
    The AI platform's own RSA keypair, used to receive encrypted responses.

    The private key is loaded from GATEWAY_CLIENT_KEY_PATH and generated on first
    use if absent, so no manual key ceremony is needed to bring the platform up.
    Point the setting at a mounted secret in production if you would rather manage
    the key outside the application.
    """

    def __init__(self):
        self._private_key = None
        self._public_key_b64: Optional[str] = None

    def _load_or_create(self):
        if self._private_key is not None:
            return

        path = settings.GATEWAY_CLIENT_KEY_PATH
        if path and os.path.exists(path):
            try:
                with open(path, "rb") as handle:
                    self._private_key = serialization.load_pem_private_key(
                        handle.read(), password=None
                    )
                logger.info(f"Loaded gateway client RSA key from {path}")
            except Exception as e:
                raise GatewayException(
                    f"Could not load the gateway client RSA key from '{path}': {e}"
                ) from e
        else:
            self._private_key = rsa.generate_private_key(
                public_exponent=65537, key_size=settings.GATEWAY_CLIENT_KEY_SIZE
            )
            logger.warning(
                "No gateway client RSA key at '%s' — generated a new %s-bit key. "
                "Responses stay readable across restarts only if this key persists.",
                path, settings.GATEWAY_CLIENT_KEY_SIZE,
            )
            if path:
                self._persist(path)

        public_der = self._private_key.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        self._public_key_b64 = base64.b64encode(public_der).decode("ascii")

    def _persist(self, path: str):
        try:
            directory = os.path.dirname(os.path.abspath(path))
            if directory:
                os.makedirs(directory, exist_ok=True)
            pem = self._private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
            with open(path, "wb") as handle:
                handle.write(pem)
            try:
                os.chmod(path, 0o600)
            except OSError:
                # Best effort — POSIX modes are not meaningful on all platforms.
                pass
            logger.info(f"Persisted the gateway client RSA key to {path}")
        except Exception as e:
            logger.warning(
                f"Could not persist the gateway client RSA key to '{path}': {e}. "
                "A fresh key will be generated on the next restart."
            )

    @property
    def public_key_b64(self) -> str:
        """Base64 X.509 SubjectPublicKeyInfo — the value for X-Frontend-Key."""
        self._load_or_create()
        return self._public_key_b64

    def unwrap_aes_key(self, wrapped: bytes) -> bytes:
        self._load_or_create()
        return self._private_key.decrypt(wrapped, OAEP_PADDING)


client_key_pair = ClientKeyPair()


def is_encrypted_envelope(payload: Any) -> bool:
    """True when resData carries an encrypted hybrid envelope rather than plain data."""
    return isinstance(payload, dict) and all(field in payload for field in ENVELOPE_FIELDS)


def _b64(value: Any, field: str) -> bytes:
    if not isinstance(value, str):
        raise GatewayException(
            f"Encrypted response field '{field}' should be a base64 string, got {type(value).__name__}."
        )
    try:
        return base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as e:
        raise GatewayException(f"Encrypted response field '{field}' is not valid base64: {e}") from e


def decrypt_envelope(envelope: Dict[str, Any], operation: str = "response") -> str:
    """
    Decrypt a `Crypto.encryptForFrontend` envelope and return the plaintext JSON.

    Raises GatewayException on a malformed envelope or a failed authentication tag
    — a bad tag means the ciphertext was altered or the wrong key was used, and
    must never be reported as an empty result.
    """
    wrapped_key = _b64(envelope.get("key"), "key")
    iv = _b64(envelope.get("iv"), "iv")
    ciphertext = _b64(envelope.get("payload"), "payload")

    if len(iv) != GCM_IV_LENGTH:
        raise GatewayException(
            f"Encrypted {operation} has a {len(iv)}-byte IV; the gateway uses {GCM_IV_LENGTH}."
        )
    if len(ciphertext) <= GCM_TAG_LENGTH:
        raise GatewayException(
            f"Encrypted {operation} payload is too short to contain a GCM tag."
        )

    try:
        aes_key = client_key_pair.unwrap_aes_key(wrapped_key)
    except Exception as e:
        raise GatewayException(
            f"Could not unwrap the AES key for the encrypted {operation}: {e}. "
            "The gateway encrypted to a different public key than this platform sent — "
            "check that GATEWAY_CLIENT_KEY_PATH is stable across restarts."
        ) from e

    try:
        # AESGCM expects the tag appended to the ciphertext, which is exactly how
        # the JCE emits it, so the payload is passed through unchanged.
        plaintext = AESGCM(aes_key).decrypt(iv, ciphertext, None)
    except InvalidTag as e:
        raise GatewayException(
            f"Authentication tag check failed on the encrypted {operation}: "
            "the payload was altered in transit or encrypted with a different key."
        ) from e

    return plaintext.decode("utf-8")


def verify_signature(envelope: Dict[str, Any], backend_public_key_b64: str) -> bool:
    """
    Verify the backend's SHA256withRSA signature over encryptedPayload || encryptedAesKey.

    Returns False when the envelope carries no signature; raises on a signature
    that is present but invalid, because a bad signature means the response did
    not come from the gateway.
    """
    signature = envelope.get("signature")
    if not signature:
        return False

    backend_key = serialization.load_der_public_key(
        _b64(backend_public_key_b64, "backendPublicKey")
    )
    signed_bytes = _b64(envelope.get("payload"), "payload") + _b64(envelope.get("key"), "key")

    try:
        backend_key.verify(
            _b64(signature, "signature"),
            signed_bytes,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True
    except InvalidSignature as e:
        raise GatewayException(
            "The encrypted response carried an invalid backend signature — it did not "
            "originate from the DigiPay gateway."
        ) from e


def frontend_key_header() -> Dict[str, str]:
    """The X-Frontend-Key header carrying this platform's public key."""
    return {"X-Frontend-Key": client_key_pair.public_key_b64}
