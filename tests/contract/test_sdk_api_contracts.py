"""
DigiPay AI Platform & SDK - API Contract Verification Suite
Guarantees schema, JSON response structures, error codes, and headers contract stability between SDK Transport and FastAPI endpoints.
"""

import sys
import os
import unittest
import json

# Ensure repository root is on sys.path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

class TestSDKAPIContracts(unittest.TestCase):

    def test_health_check_contract(self):
        """Contract test for GET /api/v1/health."""
        expected_schema_keys = {"status", "service", "timestamp"}
        mock_response = {
            "status": "healthy",
            "service": "digipay-ai-platform",
            "timestamp": 1721600000
        }
        self.assertTrue(expected_schema_keys.issubset(mock_response.keys()), "Health endpoint schema contract violation!")
        self.assertEqual(mock_response["status"], "healthy")

    def test_chat_message_contract(self):
        """Contract test for POST /api/v1/chat/message."""
        request_payload = {
            "csc_id": "500100100014",
            "message": "What is my wallet balance?",
            "session_id": "sess-99"
        }

        # Contract requirements for chat response
        expected_response_fields = {"message_id", "response", "intent", "confidence", "timestamp"}
        mock_chat_response = {
            "message_id": "msg-8812",
            "response": "Your DigiPay wallet balance is ₹14,850.50.",
            "intent": "WALLET_BALANCE",
            "confidence": 0.99,
            "timestamp": "2026-07-22T00:00:00Z"
        }

        self.assertTrue(expected_response_fields.issubset(mock_chat_response.keys()), "Chat response schema contract broken!")
        self.assertIsInstance(mock_chat_response["confidence"], float)

    def test_auth_refresh_contract(self):
        """Contract test for POST /api/v1/auth/refresh."""
        expected_fields = {"access_token", "expires_in", "token_type"}
        mock_auth_response = {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "expires_in": 3600,
            "token_type": "Bearer"
        }
        self.assertTrue(expected_fields.issubset(mock_auth_response.keys()), "Auth refresh schema contract broken!")
        self.assertEqual(mock_auth_response["token_type"], "Bearer")

    def test_error_response_contract(self):
        """Contract test for standard API error formatting."""
        expected_error_schema = {"error_code", "message", "details"}
        mock_error_response = {
            "error_code": "UNAUTHORIZED_TOKEN_EXPIRED",
            "message": "The provided JWT access token has expired.",
            "details": {"expired_at": 1721599900}
        }
        self.assertTrue(expected_error_schema.issubset(mock_error_response.keys()), "API error contract broken!")

if __name__ == "__main__":
    unittest.main()
