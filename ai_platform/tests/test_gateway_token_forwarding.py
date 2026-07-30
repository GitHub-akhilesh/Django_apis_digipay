"""
How the caller's token is presented to the DigiPay gateway.

The gateway authenticates from the `access_token` COOKIE and keeps server-side
session state. Its two rejection messages distinguish the cases, verified against
the live UAT gateway with a real session token:

    Authorization: Bearer <token>  -> "Full authentication is required to access
                                       this resource"     (credential ignored)
    Cookie: access_token=<token>   -> "Session expired"    (credential recognised)

Forwarding only the Authorization header therefore made every /v2/* call
unauthenticated regardless of how valid the token was, which surfaced to the user
as "I have flagged this for Level-2 human support".
"""

import pytest

from core.config import settings
from gateway.client import GatewayClient

TOKEN = "eyJhbGciOiJIUzI1NiJ9.payload.signature"


def test_token_is_forwarded_as_a_cookie():
    """The cookie is the credential the gateway actually reads."""
    headers = GatewayClient._prepare_headers(None, jwt_token=TOKEN)
    assert "Cookie" in headers, "the gateway reads the session from a cookie"
    assert f"{settings.GATEWAY_TOKEN_COOKIE_NAME}={TOKEN}" in headers["Cookie"]


def test_bearer_header_is_also_sent():
    """Kept for deployments that do accept a Bearer header; costs nothing."""
    headers = GatewayClient._prepare_headers(None, jwt_token=TOKEN)
    assert headers["Authorization"] == f"Bearer {TOKEN}"


def test_bearer_prefix_is_not_doubled():
    """A token arriving already prefixed must not become 'Bearer Bearer ...'."""
    headers = GatewayClient._prepare_headers(None, jwt_token=f"Bearer {TOKEN}")
    assert headers["Authorization"] == f"Bearer {TOKEN}"
    assert f"{settings.GATEWAY_TOKEN_COOKIE_NAME}={TOKEN}" in headers["Cookie"]
    assert "Bearer" not in headers["Cookie"], "the cookie must carry the bare token"


def test_existing_cookies_are_preserved():
    """Appending must not discard a cookie a caller already set."""
    headers = GatewayClient._prepare_headers({"Cookie": "theme=dark"}, jwt_token=TOKEN)
    assert "theme=dark" in headers["Cookie"]
    assert f"{settings.GATEWAY_TOKEN_COOKIE_NAME}={TOKEN}" in headers["Cookie"]


def test_cookie_forwarding_can_be_disabled(monkeypatch):
    monkeypatch.setattr(settings, "GATEWAY_FORWARD_TOKEN_AS_COOKIE", False)
    headers = GatewayClient._prepare_headers(None, jwt_token=TOKEN)
    assert "Cookie" not in headers
    assert headers["Authorization"] == f"Bearer {TOKEN}"


def test_cookie_name_is_configurable(monkeypatch):
    monkeypatch.setattr(settings, "GATEWAY_TOKEN_COOKIE_NAME", "session_jwt")
    headers = GatewayClient._prepare_headers(None, jwt_token=TOKEN)
    assert headers["Cookie"] == f"session_jwt={TOKEN}"


def test_no_token_falls_back_to_internal_auth():
    """Without a caller token, service-to-service headers are used instead."""
    headers = GatewayClient._prepare_headers(None, jwt_token=None)
    assert "Cookie" not in headers
    assert "Authorization" not in headers
    assert headers.get("X-Internal-Client") == "AI_PLATFORM"


@pytest.mark.anyio
async def test_cookie_reaches_the_outbound_request(monkeypatch):
    """End-to-end through the client: the cookie must be on the wire."""
    seen = {}

    class _Client:
        is_closed = False

        async def request(self, method, url, json=None, params=None, headers=None):
            seen.update(headers or {})

            class _R:
                status_code = 200
                text = "{}"

                def json(self):
                    return {}

            return _R()

    monkeypatch.setattr(GatewayClient, "get_client", classmethod(lambda cls: _Client()))

    await GatewayClient.request("GET", "/v2/ledger/balance", jwt_token=TOKEN)

    assert f"{settings.GATEWAY_TOKEN_COOKIE_NAME}={TOKEN}" in seen.get("Cookie", "")
