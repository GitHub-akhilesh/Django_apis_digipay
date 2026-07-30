"""
Authentication against a REAL DigiPay session token.

A live DigiPay token looks like this (signed with the shared JWT_SECRET, so it
verifies here):

    {"sub": "500100100014", "ownerId": "500100100014",
     "operatorIds": "500100100014,500100100022,500100100107",
     "roles": ["VLE", "ADMIN"], "txnId": "CZU...", "iat": ..., "exp": ...}

It differs from what this service originally assumed in three ways, each of which
caused a 401 or a silent authorisation failure:

  transport  it is delivered in the `access_token` COOKIE, and only the
             Authorization header and ?token= were read
  identity   there is no cscId/merchantId claim; the CSC ID is `ownerId`/`sub`
  roles      "VLE"/"ADMIN" do not match the ROLE_* names every tool's
             allow-list is written against
"""

import time

import jwt
import pytest
from fastapi.testclient import TestClient

from auth.identity import extract_merchant_id, extract_user_id, normalise_roles
from core.config import settings

# Mirrors a real DigiPay session payload.
DIGIPAY_CLAIMS = {
    "sub": "500100100014",
    "ownerId": "500100100014",
    "operatorIds": "500100100014,500100100022,500100100107",
    "roles": ["VLE", "ADMIN"],
    "txnId": "CZU1785383540756710ae63e4d6a41848ef",
}


def digipay_token(**overrides):
    claims = {**DIGIPAY_CLAIMS, **overrides}
    claims.setdefault("iat", int(time.time()))
    claims.setdefault("exp", int(time.time()) + 3600)
    return jwt.encode(claims, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


@pytest.fixture(scope="module")
def client():
    from main import app
    with TestClient(app) as test_client:
        yield test_client


# --------------------------------------------------------------------------- #
# Claim mapping
# --------------------------------------------------------------------------- #

def test_csc_id_resolves_from_owner_id():
    """No cscId claim exists; an empty merchant_id would break tenant isolation."""
    assert extract_merchant_id(DIGIPAY_CLAIMS) == "500100100014"


def test_csc_id_claim_precedence():
    assert extract_merchant_id({"cscId": "A", "merchantId": "B", "ownerId": "C", "sub": "D"}) == "A"
    assert extract_merchant_id({"merchantId": "B", "ownerId": "C", "sub": "D"}) == "B"
    assert extract_merchant_id({"ownerId": "C", "sub": "D"}) == "C"
    assert extract_merchant_id({"sub": "D"}) == "D"
    assert extract_merchant_id({}) == ""


def test_user_id_resolves():
    assert extract_user_id(DIGIPAY_CLAIMS) == "500100100014"


# --------------------------------------------------------------------------- #
# Role translation
# --------------------------------------------------------------------------- #

def test_vle_maps_to_merchant():
    assert "ROLE_MERCHANT" in normalise_roles(["VLE"])


def test_digipay_admin_does_not_become_a_platform_admin():
    """
    A DigiPay token carrying ownerId + operatorIds uses "ADMIN" for the owner of
    a CSC relative to its operators, not a platform administrator. Mapping it to
    ROLE_ADMIN would hand every CSC owner the platform-wide admin reports and
    exempt them from tenant isolation, so the default must not do that.
    """
    roles = normalise_roles(DIGIPAY_CLAIMS["roles"])
    assert "ROLE_ADMIN" not in roles, (
        "DigiPay ADMIN must not map to ROLE_ADMIN by default - that is a "
        "privilege escalation. Override JWT_ROLE_MAP deliberately if needed."
    )
    assert "ROLE_MERCHANT" in roles


def test_admin_mapping_is_configurable(monkeypatch):
    """A deployment whose ADMIN really is a platform admin can opt in."""
    monkeypatch.setattr(
        settings, "JWT_ROLE_MAP", "VLE=ROLE_MERCHANT,ADMIN=ROLE_ADMIN"
    )
    assert "ROLE_ADMIN" in normalise_roles(["ADMIN"])


def test_unknown_role_fails_closed():
    """An unmapped role is preserved but matches no tool's allow-list."""
    roles = normalise_roles(["SOMETHING_NEW"])
    assert roles == ["ROLE_SOMETHING_NEW"]
    from tools.registry import TOOL_REGISTRY
    for meta in TOOL_REGISTRY.values():
        assert "ROLE_SOMETHING_NEW" not in meta.roles


def test_already_prefixed_roles_pass_through():
    assert normalise_roles(["ROLE_SUPPORT"]) == ["ROLE_SUPPORT"]


def test_comma_separated_roles_string():
    assert normalise_roles("VLE,SUPPORT") == ["ROLE_MERCHANT", "ROLE_SUPPORT"]


def test_no_roles_falls_back_to_the_default():
    assert normalise_roles(None) == [settings.JWT_DEFAULT_ROLE]
    assert normalise_roles([]) == [settings.JWT_DEFAULT_ROLE]


def test_duplicate_roles_collapse():
    # VLE and MERCHANT both map to ROLE_MERCHANT.
    assert normalise_roles(["VLE", "MERCHANT"]) == ["ROLE_MERCHANT"]


# --------------------------------------------------------------------------- #
# Cookie transport
# --------------------------------------------------------------------------- #

def test_session_cookie_authenticates(client):
    """
    The regression this fixes: a browser sends the session in the access_token
    cookie, which was never read, so every request was 401 even while signed in.
    """
    response = client.post(
        "/api/v1/chat",
        json={"sessionId": "cookie-auth", "message": "what can you do"},
        cookies={"access_token": digipay_token()},
    )
    assert response.status_code == 200, response.text


def test_authorization_header_still_works(client):
    response = client.post(
        "/api/v1/chat",
        json={"sessionId": "hdr-auth", "message": "what can you do"},
        headers={"Authorization": f"Bearer {digipay_token()}"},
    )
    assert response.status_code == 200, response.text


def test_header_takes_precedence_over_cookie(client):
    """An explicit header must win, so a stale cookie cannot override it."""
    from auth.identity import extract_token

    class _Req:
        headers = {"Authorization": "Bearer header-token"}
        cookies = {"access_token": "cookie-token"}
        query_params = {}

    assert extract_token(_Req()) == "header-token"


def test_cookie_used_when_no_header():
    from auth.identity import extract_token

    class _Req:
        headers = {}
        cookies = {"access_token": "cookie-token"}
        query_params = {}

    assert extract_token(_Req()) == "cookie-token"


def test_no_credential_still_rejected(client):
    """Reading cookies must not weaken authentication."""
    response = client.post(
        "/api/v1/chat", json={"sessionId": "none", "message": "hi"}
    )
    assert response.status_code == 401


def test_expired_session_cookie_rejected(client):
    response = client.post(
        "/api/v1/chat",
        json={"sessionId": "expired", "message": "hi"},
        cookies={"access_token": digipay_token(exp=int(time.time()) - 60)},
    )
    assert response.status_code == 401


def test_tampered_cookie_rejected(client):
    """Signature verification must still apply to cookie-borne tokens."""
    forged = jwt.encode(DIGIPAY_CLAIMS, "not-the-real-secret", algorithm="HS256")
    response = client.post(
        "/api/v1/chat",
        json={"sessionId": "forged", "message": "hi"},
        cookies={"access_token": forged},
    )
    assert response.status_code == 401


# --------------------------------------------------------------------------- #
# End-to-end principal
# --------------------------------------------------------------------------- #

def test_principal_carries_csc_id_and_mapped_roles(client):
    """
    The whole chain: cookie -> verified token -> principal. An empty merchant_id
    here would silently disable tenant isolation.
    """
    from fastapi import Request

    from main import app

    seen = {}

    @app.get("/__principal_probe", include_in_schema=False)
    async def _probe(request: Request):
        principal = request.state.user
        seen["merchant_id"] = principal.merchant_id
        seen["roles"] = principal.roles
        seen["token_retained"] = bool(getattr(request.state, "access_token", None))
        return {"ok": True}

    response = client.get(
        "/__principal_probe", cookies={"access_token": digipay_token()}
    )
    assert response.status_code == 200
    assert seen["merchant_id"] == "500100100014"
    assert "ROLE_MERCHANT" in seen["roles"]
    assert seen["token_retained"], "the token must be retained for gateway forwarding"
