"""
CORS preflight regression tests.

A browser preflight is an OPTIONS request that carries NO Authorization header.
The JWT middleware used to intercept it and answer 401 *without* any
Access-Control-Allow-* headers, which browsers surface as an opaque "CORS error"
rather than an auth problem — so every cross-origin call from the React app to
POST /api/v1/chat failed with no usable diagnostic.

Two things keep that fixed and both are asserted here:
  1. CORSMiddleware is registered LAST in main.py, making it the OUTERMOST layer
     (Starlette's add_middleware prepends), so preflights are answered before
     authentication runs.
  2. The JWT middleware short-circuits OPTIONS regardless, as defence in depth.
"""

import pytest
from fastapi.testclient import TestClient
from starlette.middleware.cors import CORSMiddleware

from core.config import settings

REACT_ORIGIN = "http://localhost:5173"

# Endpoints the browser calls cross-origin. All are authenticated, which is
# exactly why their preflights must not be authenticated.
PROTECTED_PATHS = [
    "/api/v1/chat",
    "/api/v1/chat/stream",
    "/api/v1/governance/services",
]


@pytest.fixture(scope="module")
def client():
    from main import app
    with TestClient(app) as test_client:
        yield test_client


def test_cors_is_the_outermost_middleware():
    """
    If CORS is not outermost, an inner middleware can reject a preflight before
    the CORS headers are attached. Starlette prepends, so the LAST registered
    middleware is first in user_middleware.
    """
    from main import app

    classes = [m.cls for m in app.user_middleware]
    assert classes, "no middleware registered"
    assert classes[0] is CORSMiddleware, (
        "CORSMiddleware must be registered last in main.py so it is outermost; "
        f"outermost is currently {classes[0].__name__}"
    )


@pytest.mark.parametrize("path", PROTECTED_PATHS)
def test_preflight_succeeds_without_a_token(client, path):
    """The whole point: an unauthenticated OPTIONS must return CORS headers."""
    response = client.options(
        path,
        headers={
            "Origin": REACT_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )

    assert response.status_code == 200, (
        f"preflight for {path} returned {response.status_code}; "
        "the browser will report this as a CORS error"
    )
    assert "access-control-allow-origin" in response.headers, (
        f"preflight for {path} carried no Access-Control-Allow-Origin header"
    )
    allow_headers = response.headers.get("access-control-allow-headers", "").lower()
    assert "authorization" in allow_headers, (
        "Authorization must be an allowed header or the real request is blocked"
    )


def test_preflight_is_not_answered_with_an_auth_error(client):
    """Guards the specific regression: 401 on a preflight."""
    response = client.options(
        "/api/v1/chat",
        headers={
            "Origin": REACT_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code != 401
    assert "AUTH-1001" not in response.text


def test_actual_cross_origin_request_still_requires_auth(client):
    """
    CORS must not become an auth bypass: a real (non-preflight) request without a
    token must still be rejected, and should carry CORS headers so the browser can
    show the 401 to the app rather than masking it.
    """
    response = client.post(
        "/api/v1/chat",
        json={"sessionId": "cors-test", "message": "hello"},
        headers={"Origin": REACT_ORIGIN},
    )
    assert response.status_code == 401
    assert "access-control-allow-origin" in response.headers


def test_options_bypass_lives_in_the_jwt_middleware():
    """Defence in depth: the bypass must not depend on middleware ordering."""
    import inspect

    from auth.middleware import JWTAuthenticationMiddleware

    source = inspect.getsource(JWTAuthenticationMiddleware.dispatch)
    assert 'request.method == "OPTIONS"' in source, (
        "JWTAuthenticationMiddleware must short-circuit OPTIONS so a reordering "
        "of middleware cannot reintroduce 401-on-preflight"
    )


def test_origin_list_parsing():
    """A comma-separated origin list must be usable by CORSMiddleware."""
    original = settings.CORS_ALLOW_ORIGINS
    try:
        settings.CORS_ALLOW_ORIGINS = "*"
        assert settings.cors_allow_origins == ["*"]

        settings.CORS_ALLOW_ORIGINS = "http://localhost:5173, http://localhost:5174/"
        assert settings.cors_allow_origins == [
            "http://localhost:5173",
            "http://localhost:5174",
        ]
    finally:
        settings.CORS_ALLOW_ORIGINS = original
