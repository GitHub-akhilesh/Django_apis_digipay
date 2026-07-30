"""
Tests for gateway environment configuration and caller-token propagation.

Both are deployment-critical and were both wrong before: the base URL omitted the
gateway's context path, and the caller's JWT was never forwarded, so every /v2/*
data lookup would have returned 401 in production.
"""

import json
import time

import jwt
import pytest
from fastapi.testclient import TestClient

from core.config import settings
from gateway.v2.base import GatewayV2Client

PROD_HOST = "https://digipayapi.csccloud.in"
UAT_HOST = "https://digipayapiuat.csccloud.in"
UAT_GATEWAY = f"{UAT_HOST}/gateway"


# --------------------------------------------------------------------------- #
# Base URL / context path normalisation
# --------------------------------------------------------------------------- #

def test_resolved_base_url_carries_the_context_path():
    """
    gateway-service sets server.servlet.context-path=/gateway, so the resolved
    base URL must include it or every controller returns a Tomcat HTML 404.
    """
    assert settings.gateway_base_url.rstrip("/").endswith("/gateway"), (
        f"gateway_base_url={settings.gateway_base_url!r} is missing the /gateway "
        "context path; every /v2/* call would 404."
    )


@pytest.mark.parametrize("configured", [
    UAT_HOST,                 # the React VITE_API_BASE_URL spelling
    f"{UAT_HOST}/",           # trailing slash
    UAT_GATEWAY,              # already includes the context path
    f"{UAT_GATEWAY}/",
])
def test_both_url_spellings_resolve_identically(monkeypatch, configured):
    """
    The team shares the bare host (matching the React app's VITE_API_BASE_URL),
    so pasting it in must work. A missing prefix and a doubled
    /gateway/gateway both 404 with HTML, which is easy to misread as a
    non-existent endpoint - so neither may be possible from configuration.
    """
    monkeypatch.setattr(settings, "API_GATEWAY_URL", configured)
    monkeypatch.setattr(settings, "API_GATEWAY_CONTEXT_PATH", "/gateway")
    assert settings.gateway_base_url == UAT_GATEWAY


def test_context_path_can_be_disabled_for_a_stripping_proxy(monkeypatch):
    """A proxy may already strip the prefix before the gateway sees the request."""
    monkeypatch.setattr(settings, "API_GATEWAY_URL", UAT_HOST)
    monkeypatch.setattr(settings, "API_GATEWAY_CONTEXT_PATH", "")
    assert settings.gateway_base_url == UAT_HOST


def test_gateway_url_is_https():
    """Port 80 is closed on both csccloud hosts."""
    url = settings.API_GATEWAY_URL
    if "csccloud.in" in url:
        assert url.startswith("https://"), f"{url} must use HTTPS"


def test_local_config_points_at_uat_not_production():
    """A developer machine must never default to the production gateway."""
    if "csccloud.in" in settings.API_GATEWAY_URL:
        assert settings.gateway_base_url.rstrip("/") == UAT_GATEWAY, (
            "local/UAT configuration should use the UAT gateway; "
            f"got {settings.gateway_base_url!r}"
        )


def test_health_path_is_the_actuator_endpoint():
    """
    /health on the gateway sits behind Spring Security and answers 401, which
    would report a healthy gateway as DOWN.
    """
    assert settings.API_GATEWAY_HEALTH_PATH == "/actuator/health"


@pytest.mark.parametrize("service,suffix,expected_path", [
    ("user", "/publickey", "/v2/user/publickey"),
    ("txn", "/logs", "/v2/txn/logs"),
    ("ledger", "/balance", "/v2/ledger/balance"),
    ("upi", "/vpa/suggestion", "/v1/upi/vpa/suggestion"),
    ("analytics", "/analytics", "/api/v2/analytics"),
])
def test_service_prefixes_are_context_path_relative(service, suffix, expected_path):
    """
    Controller prefixes must NOT repeat /gateway — it belongs to the base URL, so
    duplicating it would produce /gateway/gateway/v2/...
    """
    path = GatewayV2Client.prefix(service) + suffix
    assert path == expected_path
    assert "gateway" not in path


def test_env_files_configure_both_environments():
    """The documented hosts must actually be present in the env files."""
    import os

    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    with open(os.path.join(root, ".env.prod"), encoding="utf-8") as handle:
        assert f"API_GATEWAY_URL={PROD_HOST}" in handle.read()

    with open(os.path.join(root, ".env.local"), encoding="utf-8") as handle:
        assert f"API_GATEWAY_URL={UAT_HOST}" in handle.read()


def test_backend_and_react_resolve_to_the_same_absolute_url():
    """
    The React app and this platform split the URL differently but must reach the
    same place: React keeps the bare host in VITE_API_BASE_URL and carries
    /gateway in each path constant, while this platform keeps the context path in
    the base so tool paths mirror the Java @RequestMapping values.
    """
    react_base = UAT_HOST                       # VITE_API_BASE_URL
    react_path = "/gateway/v2/user/publickey"   # src/constants/apiUrls.js
    react_url = react_base + react_path

    backend_path = GatewayV2Client.prefix("user") + "/publickey"
    backend_url = UAT_GATEWAY + backend_path

    assert react_url == backend_url == f"{UAT_HOST}/gateway/v2/user/publickey"


# --------------------------------------------------------------------------- #
# Caller token propagation
# --------------------------------------------------------------------------- #

def _token(roles=("ROLE_MERCHANT",)):
    return jwt.encode(
        {
            "sub": "vle1",
            "cscId": "500100100014",
            "merchantId": "500100100014",
            "roles": list(roles),
            "exp": int(time.time()) + 600,
        },
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )


def test_middleware_retains_the_verified_token():
    """
    The middleware validated the token then discarded it. It must be kept, or
    downstream gateway calls have no credential to present.
    """
    from fastapi import Request

    from main import app

    captured = {}

    @app.get("/__token_probe", include_in_schema=False)
    async def _probe(request: Request):
        captured["token"] = getattr(request.state, "access_token", None)
        return {"ok": True}

    token = _token()
    with TestClient(app) as client:
        response = client.get("/__token_probe", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert captured["token"] == token, "the verified raw token was not retained"


@pytest.mark.anyio
async def test_caller_token_reaches_the_gateway_as_a_bearer_header(monkeypatch):
    """
    End-to-end: a chat request's token must arrive on the outbound gateway call.
    Without it the gateway answers 401 "Full authentication is required".
    """
    from gateway.client import GatewayClient
    from main import app

    seen = []

    class _Response:
        status_code = 200

        def __init__(self):
            self._body = {"status": "OK", "msg": "ok", "errors": [],
                          "resData": {"totalRecords": 0, "list": []}}
            self.text = json.dumps(self._body)

        def json(self):
            return self._body

    async def _request(method, endpoint_path, **kwargs):
        seen.append({"path": endpoint_path, "jwt": kwargs.get("jwt_token")})
        return _Response()

    monkeypatch.setattr(GatewayClient, "request", _request)

    token = _token()
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/chat",
            json={"sessionId": "tok-prop", "message": "show my transaction history"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    gateway_calls = [c for c in seen if c["path"].startswith("/v2/")]
    assert gateway_calls, "no gateway call was made for a transaction-history request"
    assert gateway_calls[0]["jwt"] == token, (
        "the caller's token was not forwarded to the gateway"
    )


def test_prepare_headers_sends_bearer_when_a_token_is_supplied():
    """A supplied token must become an Authorization header, not a bypass header."""
    from gateway.client import GatewayClient

    headers = GatewayClient._prepare_headers(None, jwt_token="abc.def.ghi")
    assert headers["Authorization"] == "Bearer abc.def.ghi"
    assert "X-Internal-Secret" not in headers


def test_prepare_headers_falls_back_to_internal_auth_without_a_token():
    from gateway.client import GatewayClient

    headers = GatewayClient._prepare_headers(None, jwt_token=None)
    assert "Authorization" not in headers
    assert headers.get("X-Internal-Client") == "AI_PLATFORM"
