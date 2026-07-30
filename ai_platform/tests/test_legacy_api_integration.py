"""
Tests for the legacy DigiPay API service integration.

The legacy service (`app/main.py`) stays deployed separately on its original
URLs. These tests cover the three ways it is now integrated:

  1. as read-only chat tools calling it over HTTP,
  2. as merged paths in this service's OpenAPI schema (URLs unchanged),
  3. as an entry in the governance registers.
"""

import base64
import json

import httpx
import pytest

from core.config import settings
from core.exceptions import AuthenticationException, GatewayException
from gateway.legacy_v1.client import (
    EXCLUDED_ENDPOINTS,
    READ_ONLY_ENDPOINTS,
    LegacyV1Client,
    legacy_v1_client,
)
from messaging.tool_messages import TOOL_MESSAGES
from services.tool_executor import tool_executor_service
from tools.decorator import SOURCE_LEGACY_API
from tools.registry import TOOL_REGISTRY

LEGACY_TOOLS = ("getLegacyTxnLogs", "getLegacyPassbook", "getLegacyWalletBalance")

PASSBOOK_PAYLOAD = {
    "totalRecords": 2,
    "totalPages": 1,
    "currentPage": 1,
    "recordsPerPage": 10,
    "list": [
        {"txnDate": "10-06-2026", "txnId": "OLD001", "txnType": "CREDIT",
         "amount": 1500.0, "closingBalance": 3200.0, "remarks": "Legacy settlement"},
        {"txnDate": "11-06-2026", "txnId": "OLD002", "txnType": "DEBIT",
         "amount": 200.0, "closingBalance": 3000.0, "remarks": "Legacy payout"},
    ],
}


def enveloped(payload: dict) -> dict:
    """The legacy EnvelopedResponse: resData is BASE64-encoded JSON."""
    return {
        "status": "OK",
        "msg": "success",
        "errors": None,
        "resData": base64.b64encode(json.dumps(payload).encode()).decode(),
    }


class MockResponse:
    def __init__(self, body, status_code=200):
        self.status_code = status_code
        self._body = body
        self.text = json.dumps(body) if isinstance(body, (dict, list)) else str(body)

    def json(self):
        if isinstance(self._body, (dict, list)):
            return self._body
        raise ValueError("not json")


@pytest.fixture
def mock_legacy(monkeypatch):
    """Intercept the legacy client's HTTP calls."""
    calls = []

    class _Client:
        is_closed = False

        async def request(self, method, url, json=None, headers=None, **kwargs):
            calls.append({"method": method, "url": url, "json": json, "headers": headers or {}})
            if url.endswith("/passbook"):
                return MockResponse(enveloped(PASSBOOK_PAYLOAD))
            if url.endswith("/txn-logs"):
                return MockResponse(enveloped({"totalRecords": 0, "list": []}))
            if url.endswith("/wallet_balance"):
                # This route returns a bare map, not the envelope.
                return MockResponse({"500100100014": 4560.50})
            return MockResponse(enveloped({}))

    monkeypatch.setattr(LegacyV1Client, "_get_client", classmethod(lambda cls: _Client()))
    LegacyV1Client._breaker = None
    return calls


# --------------------------------------------------------------------------- #
# 1. Read-only enforcement
# --------------------------------------------------------------------------- #

@pytest.mark.anyio
async def test_auth_token_endpoint_is_blocked(mock_legacy):
    with pytest.raises(AuthenticationException) as exc:
        await legacy_v1_client.call("POST", "/auth/token", "x")
    assert "AUTH" in str(exc.value.developer_message)
    assert mock_legacy == []


@pytest.mark.anyio
async def test_agent_endpoints_are_blocked_to_prevent_recursion(mock_legacy):
    """The legacy service has its own chat agent; calling it from chat would loop."""
    with pytest.raises(AuthenticationException) as exc:
        await legacy_v1_client.call("POST", "/agent/chat", "x")
    assert "RECURSION" in str(exc.value.developer_message)


@pytest.mark.anyio
async def test_daywise_report_is_blocked_as_unsupported(mock_legacy):
    with pytest.raises(AuthenticationException) as exc:
        await legacy_v1_client.call("POST", "/daywise_report", "x")
    assert "UNSUPPORTED" in str(exc.value.developer_message)


@pytest.mark.anyio
async def test_unlisted_legacy_path_is_blocked(mock_legacy):
    with pytest.raises(AuthenticationException):
        await legacy_v1_client.call("POST", "/invented", "x")
    assert mock_legacy == []


def test_allow_list_and_exclusions_do_not_overlap():
    allowed = {(m, p) for m, p, _ in READ_ONLY_ENDPOINTS}
    excluded = {(m, p) for m, p, _, _ in EXCLUDED_ENDPOINTS}
    assert allowed & excluded == set()


def test_all_legacy_tools_are_read_only():
    offenders = [
        m.name for m in TOOL_REGISTRY.values()
        if m.source == SOURCE_LEGACY_API and not m.read_only
    ]
    assert offenders == []


# --------------------------------------------------------------------------- #
# 2. Envelope handling
# --------------------------------------------------------------------------- #

@pytest.mark.anyio
async def test_base64_res_data_is_decoded(mock_legacy):
    """
    The legacy envelope carries base64-encoded JSON. Without decoding, chat would
    render an opaque blob at the user.
    """
    result = await legacy_v1_client.call(
        "POST", "/passbook", "legacyPassbook",
        json_data={"cscId": "500100100014", "fromDate": "01-06-2026", "toDate": "30-06-2026"},
    )
    assert result["totalRecords"] == 2
    assert result["list"][0]["txnId"] == "OLD001"


@pytest.mark.anyio
async def test_bare_object_response_passes_through(mock_legacy):
    """/wallet_balance returns a plain map rather than the envelope."""
    result = await legacy_v1_client.call(
        "POST", "/wallet_balance", "legacyWalletBalance",
        json_data={"csc_ids": ["500100100014"]},
    )
    assert result == {"500100100014": 4560.50}


@pytest.mark.anyio
async def test_non_ok_status_raises(monkeypatch):
    class _Client:
        is_closed = False

        async def request(self, *args, **kwargs):
            return MockResponse({"status": "ERR", "msg": "Invalid cscId", "resData": ""})

    monkeypatch.setattr(LegacyV1Client, "_get_client", classmethod(lambda cls: _Client()))
    LegacyV1Client._breaker = None

    with pytest.raises(GatewayException) as exc:
        await legacy_v1_client.call("POST", "/passbook", "x", json_data={"cscId": "1"})
    assert "Invalid cscId" in str(exc.value.developer_message)


@pytest.mark.anyio
async def test_http_error_raises_with_the_service_named(monkeypatch):
    class _Client:
        is_closed = False

        async def request(self, *args, **kwargs):
            return MockResponse({"detail": "boom"}, status_code=500)

    monkeypatch.setattr(LegacyV1Client, "_get_client", classmethod(lambda cls: _Client()))
    LegacyV1Client._breaker = None

    with pytest.raises(GatewayException) as exc:
        await legacy_v1_client.call("POST", "/passbook", "x", json_data={"cscId": "1"})
    assert "Legacy DigiPay service returned HTTP 500" in str(exc.value.developer_message)


@pytest.mark.anyio
async def test_unreachable_service_names_the_base_url(monkeypatch):
    """The error must say which service is down and where it was expected."""
    class _Client:
        is_closed = False

        async def request(self, *args, **kwargs):
            raise httpx.ConnectError("all connection attempts failed")

    monkeypatch.setattr(LegacyV1Client, "_get_client", classmethod(lambda cls: _Client()))
    LegacyV1Client._breaker = None

    with pytest.raises(GatewayException) as exc:
        await legacy_v1_client.call("POST", "/passbook", "x", json_data={"cscId": "1"})
    message = str(exc.value.developer_message)
    assert "Legacy DigiPay service unreachable" in message
    assert settings.LEGACY_API_URL in message


# --------------------------------------------------------------------------- #
# 3. Authentication to the legacy service
# --------------------------------------------------------------------------- #

@pytest.mark.anyio
async def test_internal_bypass_headers_used_without_a_jwt(mock_legacy):
    await legacy_v1_client.call(
        "POST", "/passbook", "x",
        json_data={"cscId": "500100100014", "fromDate": "01-06-2026", "toDate": "30-06-2026"},
    )
    headers = mock_legacy[-1]["headers"]
    assert headers["X-Client-Id"] == settings.LEGACY_INTERNAL_CLIENT_ID
    assert headers["X-Bypass-Secret"] == settings.INTERNAL_BYPASS_SECRET
    assert "Authorization" not in headers


@pytest.mark.anyio
async def test_caller_jwt_is_forwarded_when_present(mock_legacy):
    """Forwarding the user's token lets the legacy service see the real end user."""
    await legacy_v1_client.call(
        "POST", "/passbook", "x",
        json_data={"cscId": "500100100014", "fromDate": "01-06-2026", "toDate": "30-06-2026"},
        jwt_token="abc.def.ghi",
    )
    headers = mock_legacy[-1]["headers"]
    assert headers["Authorization"] == "Bearer abc.def.ghi"
    assert "X-Bypass-Secret" not in headers


@pytest.mark.anyio
async def test_original_legacy_url_is_preserved(mock_legacy):
    """The whole point: legacy URLs must not be rewritten."""
    await legacy_v1_client.call(
        "POST", "/txn-logs", "x",
        json_data={"cscId": "500100100014", "type": "AEPS_CASH_WITHDRAWAL",
                   "fromDate": "01-06-2026", "toDate": "30-06-2026"},
    )
    assert mock_legacy[-1]["url"] == "/api/v1/txn-logs"


# --------------------------------------------------------------------------- #
# 4. Tools and rendering
# --------------------------------------------------------------------------- #

def test_legacy_tools_are_registered_with_their_endpoints():
    for name in LEGACY_TOOLS:
        assert name in TOOL_REGISTRY, f"{name} not registered"
        meta = TOOL_REGISTRY[name]
        assert meta.source == SOURCE_LEGACY_API
        assert meta.endpoint.startswith("POST /api/v1/")


def test_legacy_tools_have_chat_wording_naming_the_system():
    """A user must be able to tell which system a figure came from."""
    for name in LEGACY_TOOLS:
        assert name in TOOL_MESSAGES
        msg = TOOL_MESSAGES[name]
        assert "legacy" in msg.label.lower() or "legacy" in (msg.footnote or "").lower()


@pytest.mark.anyio
async def test_legacy_passbook_tool_renders_a_table(mock_legacy):
    res = await tool_executor_service.execute_tool(
        tool_name="getLegacyPassbook",
        args={"cscId": "500100100014", "fromDate": "01-06-2026", "toDate": "30-06-2026"},
        user_roles=["ROLE_MERCHANT"],
        caller_merchant_id="500100100014",
    )
    message = res["message"]
    assert "legacy" in message.lower()
    assert "₹1,500.00" in message
    assert "OLD001" in message
    assert "2 records in total" in message


@pytest.mark.anyio
async def test_legacy_wallet_balance_tool_flattens_the_map(mock_legacy):
    res = await tool_executor_service.execute_tool(
        tool_name="getLegacyWalletBalance",
        args={"cscId": "500100100014"},
        user_roles=["ROLE_MERCHANT"],
        caller_merchant_id="500100100014",
    )
    assert res["result"] == {"cscId": "500100100014", "balance": 4560.50}
    assert "₹4,560.50" in res["message"]


@pytest.mark.anyio
async def test_legacy_tool_enforces_tenant_isolation(mock_legacy):
    with pytest.raises(AuthenticationException):
        await tool_executor_service.execute_tool(
            tool_name="getLegacyPassbook",
            args={"cscId": "500100100099", "fromDate": "01-06-2026", "toDate": "30-06-2026"},
            user_roles=["ROLE_MERCHANT"],
            caller_merchant_id="500100100014",
        )
    assert mock_legacy == []


@pytest.mark.anyio
async def test_a_new_question_does_not_replay_the_previous_answer(mock_legacy):
    """
    Regression guard: plan_outcomes used to survive a completed turn in session
    memory, so the next question's reply re-rendered the previous answer too —
    asking about the passbook returned the passbook AND the earlier balance.
    """
    from agent.orchestrator import AgentOrchestrator
    from memory.session import session_metadata_memory

    session = "session_no_replay"
    session_metadata_memory.save_metadata(session, {})

    first = await AgentOrchestrator.chat(
        session_id=session, message="what is my old digipay balance",
        csc_id="500100100014", history=[], user_roles=["ROLE_MERCHANT"],
    )
    assert "balance" in first["response"].lower()

    second = await AgentOrchestrator.chat(
        session_id=session, message="show my legacy passbook",
        csc_id="500100100014", history=[], user_roles=["ROLE_MERCHANT"],
    )
    assert "passbook" in second["response"].lower()
    assert "wallet balance" not in second["response"].lower(), (
        "the previous turn's answer leaked into this reply"
    )


@pytest.mark.anyio
async def test_legacy_txn_logs_requires_a_service_type():
    from core.exceptions import ValidationException
    from tools.legacy_v1.digipay_ops import get_legacy_txn_logs

    with pytest.raises(ValidationException):
        await get_legacy_txn_logs(
            csc_id="500100100014", type="", from_date="01-06-2026", to_date="30-06-2026"
        )


# --------------------------------------------------------------------------- #
# 5. OpenAPI aggregation — one Swagger page, unchanged URLs
# --------------------------------------------------------------------------- #

def test_legacy_paths_appear_in_this_services_schema():
    from api.openapi_aggregate import reset_cache
    from main import app

    reset_cache()
    app.openapi_schema = None
    app._openapi_merged = False

    spec = app.openapi()
    paths = spec["paths"]

    for legacy_path in ("/api/v1/txn-logs", "/api/v1/passbook", "/api/v1/wallet_balance"):
        assert legacy_path in paths, f"{legacy_path} missing from the merged schema"

    # This service's own endpoints must survive the merge.
    for own_path in ("/api/v1/chat", "/api/v1/governance/capabilities"):
        assert own_path in paths


def test_legacy_paths_carry_a_servers_override_to_the_legacy_service():
    """
    Without a per-path `servers` entry, "Try it out" would POST to this service
    and 404, because the legacy routes are served by a different process.
    """
    from main import app

    spec = app.openapi()
    entry = spec["paths"]["/api/v1/txn-logs"]
    assert entry["servers"][0]["url"] == settings.legacy_api_public_url


def test_documented_url_is_the_browser_facing_one(monkeypatch):
    """
    Under Docker the services talk over http://legacy-api:8000, which no browser
    can resolve. The schema must advertise the public address instead, or Swagger
    "Try it out" fails against a private hostname.
    """
    from api.openapi_aggregate import merge_legacy_openapi, reset_cache

    monkeypatch.setattr(settings, "LEGACY_API_URL", "http://legacy-api:8000")
    monkeypatch.setattr(settings, "LEGACY_API_PUBLIC_URL", "http://localhost:8000")
    reset_cache()

    schema = merge_legacy_openapi({"paths": {}, "components": {}})
    assert schema["paths"]["/api/v1/txn-logs"]["servers"][0]["url"] == "http://localhost:8000"
    reset_cache()


def test_public_url_falls_back_to_the_service_url_when_unset(monkeypatch):
    monkeypatch.setattr(settings, "LEGACY_API_URL", "http://127.0.0.1:8000")
    monkeypatch.setattr(settings, "LEGACY_API_PUBLIC_URL", "")
    assert settings.legacy_api_public_url == "http://127.0.0.1:8000"


def test_merged_legacy_operations_are_tagged_and_attributed():
    from api.openapi_aggregate import LEGACY_TAG
    from main import app

    spec = app.openapi()
    operation = spec["paths"]["/api/v1/passbook"]["post"]
    assert operation["tags"] == [LEGACY_TAG]
    assert "Legacy service" in operation["summary"]
    assert settings.LEGACY_API_URL in operation["description"]


def test_shared_path_keeps_this_services_definition():
    """
    Both services expose /api/v1/chat. The merge must not let the legacy alias
    replace this service's real chat endpoint.
    """
    from main import app

    spec = app.openapi()
    chat = spec["paths"]["/api/v1/chat"]
    # Ours has no legacy servers override and is not tagged as legacy.
    assert "servers" not in chat
    from api.openapi_aggregate import LEGACY_TAG
    assert LEGACY_TAG not in chat["post"].get("tags", [])


def test_aggregation_can_be_switched_off(monkeypatch):
    from api.openapi_aggregate import merge_legacy_openapi, reset_cache

    monkeypatch.setattr(settings, "AGGREGATE_LEGACY_OPENAPI", False)
    reset_cache()

    schema = {"paths": {"/api/v1/chat": {}}, "components": {}}
    assert merge_legacy_openapi(schema)["paths"] == {"/api/v1/chat": {}}
    reset_cache()


# --------------------------------------------------------------------------- #
# 6. Governance registers
# --------------------------------------------------------------------------- #

def test_legacy_endpoints_appear_in_the_governance_registers():
    from gateway.legacy_v1.client import describe_allow_list, describe_exclusions

    allowed = describe_allow_list()
    assert all(item["service"] == "legacy-digipay-api" for item in allowed)
    assert any(item["path"] == "/api/v1/txn-logs" for item in allowed)

    excluded = describe_exclusions()
    assert any(
        item["path"] == "/api/v1/auth/token" and item["reason"] == "AUTH"
        for item in excluded
    )
