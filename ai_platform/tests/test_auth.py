import pytest
# pyrefly: ignore [missing-import]
import jwt
from datetime import datetime, UTC
from fastapi.testclient import TestClient
from main import app
from core.config import settings
from core.error_codes import ErrorCode
from core.validators import validate_jwt_format, sanitize_message_input
from core.exceptions import AuthenticationException, ValidationException

client = TestClient(app)

def generate_test_token(csc_id: str = "500100100014") -> str:
    payload = {
        "sub": "testuser",
        "cscId": csc_id,
        "roles": ["ROLE_USER", "ROLE_MERCHANT"],
        "exp": int(datetime.now(UTC).timestamp()) + 3600
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def test_jwt_authentication_rejection_and_api_response():
    response = client.post("/api/v1/chat", json={"sessionId": "123", "message": "hello"})
    assert response.status_code == 401
    assert response.json()["success"] is False
    assert response.json()["errorCode"] == ErrorCode.AUTH_MISSING_TOKEN.value

def test_jwt_authentication_success_and_api_response(monkeypatch):
    token = generate_test_token()
    headers = {"Authorization": f"Bearer {token}"}

    class MockResponse:
        status_code = 200
        text = "{}"
        def json(self):
            return {
                "success": True,
                "message": "Mock Success",
                "data": {"response": "Mocked response", "intent": "INFO", "escalate": False, "policyChecked": True}
            }

    async def mock_request(*args, **kwargs):
        return MockResponse()

    # monkeypatch, not a bare assignment: `GatewayClient.request = mock_request`
    # is never undone, so it leaked into every test that ran afterwards and
    # silently replaced the real HTTP client for the rest of the session.
    from gateway.client import GatewayClient
    monkeypatch.setattr(GatewayClient, "request", mock_request)

    response = client.post("/api/v1/chat", json={"sessionId": "123", "message": "hello"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["success"] is True

def test_payload_sanitization_validator():
    raw_message = "Verify balance for \u2126 values \x00\x08"
    clean = sanitize_message_input(raw_message)
    assert "\u2126" not in clean
    assert "\u03a9" in clean
    
    raw_message_spaces = "Check    my    wallet   balance"
    clean_spaces = sanitize_message_input(raw_message_spaces)
    assert clean_spaces == "Check my wallet balance"

    with pytest.raises(ValidationException):
        sanitize_message_input("   ")

def test_jwt_format_validator():
    token = generate_test_token()
    assert validate_jwt_format(token) == token
    
    with pytest.raises(AuthenticationException):
        validate_jwt_format("invalidtoken")
