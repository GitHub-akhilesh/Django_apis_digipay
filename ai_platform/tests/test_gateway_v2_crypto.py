"""
Tests for the encrypted-response path on GET /v2/ledger/balance.

The `emulate_encrypt_for_frontend` helper is a line-by-line Python port of
`com.digipay.common.utils.Crypto#encryptForFrontend`:

    AES-256 key, 12-byte GCM IV, AES/GCM/NoPadding with a 128-bit tag,
    the AES key wrapped with RSA/ECB/OAEPWithSHA-256AndMGF1Padding,
    and SHA256withRSA over encryptedPayload || encryptedAesKey.

If the platform can decrypt what that helper produces, it can decrypt what the
gateway produces.
"""

import base64
import json
import os

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from core.exceptions import GatewayException
from gateway.client import GatewayClient
from gateway.v2.crypto import (
    ClientKeyPair,
    client_key_pair,
    decrypt_envelope,
    frontend_key_header,
    is_encrypted_envelope,
    verify_signature,
)
from gateway.v2.ledger_client import ledger_v2_client

BALANCE_JSON = json.dumps({
    "cscId": "500100100014",
    "balance": 4560.50,
    "blockedAmount": 120.0,
    "lastUpdated": "29-07-2026 10:00:00",
})


# --------------------------------------------------------------------------- #
# Java-side emulation
# --------------------------------------------------------------------------- #

def emulate_encrypt_for_frontend(plain_json: str, frontend_public_key_b64: str, backend_private_key=None):
    """Produce the same envelope shape the gateway returns in resData."""
    frontend_key = serialization.load_der_public_key(
        base64.b64decode(frontend_public_key_b64)
    )

    aes_key = AESGCM.generate_key(bit_length=256)
    iv = os.urandom(12)
    # AESGCM appends the 128-bit tag, matching the JCE.
    encrypted_payload = AESGCM(aes_key).encrypt(iv, plain_json.encode("utf-8"), None)

    encrypted_aes_key = frontend_key.encrypt(
        aes_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )

    envelope = {
        "payload": base64.b64encode(encrypted_payload).decode(),
        "iv": base64.b64encode(iv).decode(),
        "key": base64.b64encode(encrypted_aes_key).decode(),
    }

    if backend_private_key is not None:
        signature = backend_private_key.sign(
            encrypted_payload + encrypted_aes_key,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        envelope["signature"] = base64.b64encode(signature).decode()

    return envelope


@pytest.fixture(scope="module")
def backend_keypair():
    """Stands in for backend-keystore.p12 (alias backend-rsa)."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_b64 = base64.b64encode(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    ).decode()
    return private_key, public_b64


# --------------------------------------------------------------------------- #
# The header
# --------------------------------------------------------------------------- #

def test_frontend_key_header_is_base64_x509_public_key():
    """
    X-Frontend-Key must be a base64 X.509 SubjectPublicKeyInfo, because the
    gateway feeds it straight to Crypto.decodeRSAPublicKey, which uses
    X509EncodedKeySpec.
    """
    header = frontend_key_header()
    assert "X-Frontend-Key" in header

    der = base64.b64decode(header["X-Frontend-Key"], validate=True)
    loaded = serialization.load_der_public_key(der)   # would raise if malformed
    assert isinstance(loaded, rsa.RSAPublicKey)
    assert loaded.key_size >= 2048


def test_header_carries_a_public_key_only():
    """The header must never leak private key material."""
    value = frontend_key_header()["X-Frontend-Key"]
    decoded = base64.b64decode(value)
    with pytest.raises(Exception):
        serialization.load_der_private_key(decoded, password=None)


def test_key_is_stable_across_calls():
    """
    The key must not change between the request and the response, or the reply
    becomes undecryptable.
    """
    assert frontend_key_header() == frontend_key_header()


def test_keypair_persists_to_disk_and_reloads(tmp_path, monkeypatch):
    """A restart must reuse the same key, not mint a new one."""
    from core.config import settings

    key_path = tmp_path / "nested" / "client_rsa.pem"
    monkeypatch.setattr(settings, "GATEWAY_CLIENT_KEY_PATH", str(key_path))

    first = ClientKeyPair().public_key_b64
    assert key_path.exists(), "the generated key should have been written to disk"

    second = ClientKeyPair().public_key_b64
    assert first == second, "a reloaded keypair must present the same public key"


# --------------------------------------------------------------------------- #
# Envelope detection and decryption
# --------------------------------------------------------------------------- #

def test_envelope_detection():
    assert is_encrypted_envelope({"key": "a", "iv": "b", "payload": "c"})
    assert is_encrypted_envelope({"key": "a", "iv": "b", "payload": "c", "signature": "d"})
    # Plain balance data must not be mistaken for an envelope.
    assert not is_encrypted_envelope({"cscId": "500100100014", "balance": 10.0})
    assert not is_encrypted_envelope({"key": "a", "iv": "b"})
    assert not is_encrypted_envelope(None)
    assert not is_encrypted_envelope(["key", "iv", "payload"])


def test_round_trip_decrypts_the_gateway_envelope():
    envelope = emulate_encrypt_for_frontend(
        BALANCE_JSON, frontend_key_header()["X-Frontend-Key"]
    )
    recovered = json.loads(decrypt_envelope(envelope))
    assert recovered["balance"] == 4560.50
    assert recovered["cscId"] == "500100100014"


def test_tampered_payload_is_rejected():
    """A GCM tag failure must raise, never silently yield an empty result."""
    envelope = emulate_encrypt_for_frontend(
        BALANCE_JSON, frontend_key_header()["X-Frontend-Key"]
    )
    raw = bytearray(base64.b64decode(envelope["payload"]))
    raw[0] ^= 0xFF
    envelope["payload"] = base64.b64encode(bytes(raw)).decode()

    with pytest.raises(GatewayException) as exc:
        decrypt_envelope(envelope)
    assert "Authentication tag" in str(exc.value.developer_message)


def test_envelope_encrypted_to_a_different_key_is_rejected():
    """Explains the stale-key failure mode rather than surfacing a raw crypto error."""
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    other_public_b64 = base64.b64encode(
        other.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    ).decode()

    envelope = emulate_encrypt_for_frontend(BALANCE_JSON, other_public_b64)

    with pytest.raises(GatewayException) as exc:
        decrypt_envelope(envelope)
    assert "GATEWAY_CLIENT_KEY_PATH" in str(exc.value.developer_message)


@pytest.mark.parametrize("field", ["key", "iv", "payload"])
def test_malformed_base64_is_reported_per_field(field):
    envelope = emulate_encrypt_for_frontend(
        BALANCE_JSON, frontend_key_header()["X-Frontend-Key"]
    )
    envelope[field] = "not!valid!base64"

    with pytest.raises(GatewayException) as exc:
        decrypt_envelope(envelope)
    assert field in str(exc.value.developer_message)


def test_wrong_iv_length_is_reported():
    envelope = emulate_encrypt_for_frontend(
        BALANCE_JSON, frontend_key_header()["X-Frontend-Key"]
    )
    envelope["iv"] = base64.b64encode(os.urandom(16)).decode()

    with pytest.raises(GatewayException) as exc:
        decrypt_envelope(envelope)
    assert "IV" in str(exc.value.developer_message)


# --------------------------------------------------------------------------- #
# Signature verification
# --------------------------------------------------------------------------- #

def test_valid_backend_signature_verifies(backend_keypair):
    private_key, public_b64 = backend_keypair
    envelope = emulate_encrypt_for_frontend(
        BALANCE_JSON, frontend_key_header()["X-Frontend-Key"], backend_private_key=private_key
    )
    assert verify_signature(envelope, public_b64) is True


def test_missing_signature_reports_unverified_rather_than_failing(backend_keypair):
    _, public_b64 = backend_keypair
    envelope = emulate_encrypt_for_frontend(
        BALANCE_JSON, frontend_key_header()["X-Frontend-Key"]
    )
    assert verify_signature(envelope, public_b64) is False


def test_forged_signature_is_rejected(backend_keypair):
    """A signature from the wrong key means the response is not from the gateway."""
    _, public_b64 = backend_keypair
    impostor = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    envelope = emulate_encrypt_for_frontend(
        BALANCE_JSON, frontend_key_header()["X-Frontend-Key"], backend_private_key=impostor
    )

    with pytest.raises(GatewayException) as exc:
        verify_signature(envelope, public_b64)
    assert "did not" in str(exc.value.developer_message)


# --------------------------------------------------------------------------- #
# End-to-end through the ledger client
# --------------------------------------------------------------------------- #

class MockResponse:
    def __init__(self, body):
        self.status_code = 200
        self._body = body
        self.text = json.dumps(body)

    def json(self):
        return self._body


@pytest.mark.anyio
async def test_ledger_balance_is_decrypted_end_to_end(monkeypatch, backend_keypair):
    """
    The tool must return the plaintext balance, and must have advertised its own
    public key in X-Frontend-Key on the way out.
    """
    private_key, public_b64 = backend_keypair
    sent_headers = {}

    async def _request(method, endpoint_path, **kwargs):
        if endpoint_path == "/v2/user/publickey":
            return MockResponse({"status": "OK", "msg": "ok", "resData": public_b64})

        sent_headers.update(kwargs.get("headers") or {})
        envelope = emulate_encrypt_for_frontend(
            BALANCE_JSON,
            (kwargs.get("headers") or {})["X-Frontend-Key"],
            backend_private_key=private_key,
        )
        return MockResponse({"status": "OK", "msg": "SUCCESS", "resData": envelope})

    monkeypatch.setattr(GatewayClient, "request", _request)

    result = await ledger_v2_client.balance("500100100014")

    assert result["balance"] == 4560.50
    assert result["blockedAmount"] == 120.0
    assert sent_headers["X-Frontend-Key"] == client_key_pair.public_key_b64


@pytest.mark.anyio
async def test_unencrypted_error_body_passes_through(monkeypatch):
    """
    The gateway returns a plain body on some paths; that must not be run through
    the decryptor.
    """
    async def _request(method, endpoint_path, **kwargs):
        return MockResponse({
            "status": "OK", "msg": "SUCCESS",
            "resData": {"cscId": "500100100014", "balance": 0.0},
        })

    monkeypatch.setattr(GatewayClient, "request", _request)

    result = await ledger_v2_client.balance("500100100014")
    assert result == {"cscId": "500100100014", "balance": 0.0}


@pytest.mark.anyio
async def test_balance_still_returned_when_public_key_lookup_fails(monkeypatch, backend_keypair):
    """
    Signature verification is best-effort: losing the public-key endpoint must not
    take balance lookups down with it.
    """
    private_key, _ = backend_keypair

    async def _request(method, endpoint_path, **kwargs):
        if endpoint_path == "/v2/user/publickey":
            return MockResponse({"status": "ERR", "msg": "Backend public key not loaded"})
        envelope = emulate_encrypt_for_frontend(
            BALANCE_JSON,
            (kwargs.get("headers") or {})["X-Frontend-Key"],
            backend_private_key=private_key,
        )
        return MockResponse({"status": "OK", "msg": "SUCCESS", "resData": envelope})

    monkeypatch.setattr(GatewayClient, "request", _request)

    result = await ledger_v2_client.balance("500100100014")
    assert result["balance"] == 4560.50


@pytest.mark.anyio
async def test_forged_response_signature_fails_the_lookup(monkeypatch, backend_keypair):
    """A response signed by the wrong key must not be reported as a balance."""
    _, public_b64 = backend_keypair
    impostor = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    async def _request(method, endpoint_path, **kwargs):
        if endpoint_path == "/v2/user/publickey":
            return MockResponse({"status": "OK", "msg": "ok", "resData": public_b64})
        envelope = emulate_encrypt_for_frontend(
            BALANCE_JSON,
            (kwargs.get("headers") or {})["X-Frontend-Key"],
            backend_private_key=impostor,
        )
        return MockResponse({"status": "OK", "msg": "SUCCESS", "resData": envelope})

    monkeypatch.setattr(GatewayClient, "request", _request)

    with pytest.raises(GatewayException):
        await ledger_v2_client.balance("500100100014")


@pytest.mark.anyio
async def test_rendered_message_uses_the_decrypted_figures(monkeypatch, backend_keypair):
    """The chat reply must show the decrypted balance, formatted by the catalogue."""
    from services.tool_executor import tool_executor_service

    private_key, public_b64 = backend_keypair

    async def _request(method, endpoint_path, **kwargs):
        if endpoint_path == "/v2/user/publickey":
            return MockResponse({"status": "OK", "msg": "ok", "resData": public_b64})
        envelope = emulate_encrypt_for_frontend(
            BALANCE_JSON,
            (kwargs.get("headers") or {})["X-Frontend-Key"],
            backend_private_key=private_key,
        )
        return MockResponse({"status": "OK", "msg": "SUCCESS", "resData": envelope})

    monkeypatch.setattr(GatewayClient, "request", _request)

    res = await tool_executor_service.execute_tool(
        tool_name="getLedgerBalanceV2",
        args={"cscId": "500100100014"},
        user_roles=["ROLE_MERCHANT"],
        caller_merchant_id="500100100014",
    )

    assert "₹4,560.50" in res["message"]
    assert "₹120.00" in res["message"]
