"""
Base64-encoded gateway payloads, and the prompt-injection-by-accident it caused.

Several DigiPay gateway controllers return `resData` as base64-encoded JSON
rather than a plain object — /v2/device/list, /v2/ledger/passbook and
/v2/txn/logs all do. The DigiPay web app decodes it with `decodeParams`
(atob + JSON.parse); this service did not, which produced two distinct bugs:

  1. The raw base64 was rendered at the user, e.g. the device list answered
     "eyJkZXZpY2VzIjpbXSwiY3NjSWQiOiI1MDAxMDAxMDAwMTQifQ==".

  2. That base64 was also embedded in the response-formatting prompt. The offline
     LLM simulator selected its stage by scanning the prompt for substrings like
     "dag", and arbitrary base64 readily contains them — so a passbook lookup was
     answered with raw planner JSON:
     {"planner_confidence": 0.95, "steps": [{"tool": "getLedgerPassbookV2" ...}]}
"""

import base64
import json

import pytest

from gateway.client import GatewayClient
from gateway.v2.base import GatewayV2Client
from llm.provider import BaseLLMProvider


def b64(payload) -> str:
    return base64.b64encode(json.dumps(payload).encode()).decode()


class MockResponse:
    def __init__(self, body, status_code=200):
        self.status_code = status_code
        self._body = body
        self.text = json.dumps(body)

    def json(self):
        return self._body


def envelope(res_data, status="OK", msg="SUCCESS", errors=None):
    return {"status": status, "msg": msg, "errors": errors or [], "resData": res_data}


# --------------------------------------------------------------------------- #
# Decoding
# --------------------------------------------------------------------------- #

@pytest.mark.anyio
async def test_base64_device_list_is_decoded(monkeypatch):
    """The exact payload that surfaced as raw base64 in the chat window."""
    raw = "eyJkZXZpY2VzIjpbXSwiY3NjSWQiOiI1MDAxMDAxMDAwMTQifQ=="

    async def _request(method, endpoint_path, **kwargs):
        return MockResponse(envelope(raw))

    monkeypatch.setattr(GatewayClient, "request", _request)

    result = await GatewayV2Client.call(
        method="POST", path="/v2/device/list", service="device", operation="listDevices",
        json_data={"cscId": "500100100014"},
    )
    assert result == {"devices": [], "cscId": "500100100014"}


@pytest.mark.anyio
async def test_base64_paginated_payload_is_decoded(monkeypatch):
    page = {
        "totalRecords": 2,
        "list": [
            {"txnDate": "28-07-2026", "txnId": "AEP1", "amount": 2000.0, "status": "SUCCESS"},
            {"txnDate": "27-07-2026", "txnId": "AEP2", "amount": 500.0, "status": "FAILED"},
        ],
    }

    async def _request(method, endpoint_path, **kwargs):
        return MockResponse(envelope(b64(page)))

    monkeypatch.setattr(GatewayClient, "request", _request)

    result = await GatewayV2Client.call(
        method="POST", path="/v2/txn/logs", service="txn", operation="txnLogs",
        json_data={"cscId": "500100100014", "type": "ALL"},
    )
    assert result["totalRecords"] == 2
    assert result["list"][0]["txnId"] == "AEP1"


@pytest.mark.anyio
async def test_plain_object_payload_is_untouched(monkeypatch):
    """A controller returning a plain object must keep working."""
    async def _request(method, endpoint_path, **kwargs):
        return MockResponse(envelope({"cscId": "500100100014", "walletBalance": 4560.5}))

    monkeypatch.setattr(GatewayClient, "request", _request)

    result = await GatewayV2Client.call(
        method="GET", path="/v2/user/publickey", service="user", operation="publicKey",
    )
    assert result == {"cscId": "500100100014", "walletBalance": 4560.5}


@pytest.mark.anyio
async def test_non_base64_string_payload_is_untouched(monkeypatch):
    """GET /v2/user/publickey returns a bare base64 KEY, which is not JSON."""
    key = (
        "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAtL4OO/C3Ib0UeQ3vS6TGbzRL"
        "j0kXuJu96SBZgN2WcH3jUONw"
    )

    async def _request(method, endpoint_path, **kwargs):
        return MockResponse(envelope(key))

    monkeypatch.setattr(GatewayClient, "request", _request)

    result = await GatewayV2Client.call(
        method="GET", path="/v2/user/publickey", service="user", operation="publicKey",
    )
    # Must survive as the original string - decoding it would corrupt the key.
    assert result == key


@pytest.mark.anyio
async def test_rejection_reason_is_surfaced(monkeypatch):
    """
    /v2/txn/logs answers 200 with a non-OK envelope and an empty msg when a
    required field is missing. "The gateway rejected the request" alone gave
    nothing to act on, so the status and payload are now included.
    """
    from core.exceptions import GatewayException

    async def _request(method, endpoint_path, **kwargs):
        return MockResponse({"status": "VAR", "msg": None, "errors": [], "resData": None})

    monkeypatch.setattr(GatewayClient, "request", _request)

    with pytest.raises(GatewayException) as exc:
        await GatewayV2Client.call(
            method="POST", path="/v2/txn/logs", service="txn", operation="txnLogs",
            json_data={"cscId": "500100100014"},
        )
    assert "status=VAR" in str(exc.value.developer_message)


def test_txn_logs_always_sends_the_required_type():
    """
    The gateway requires `type` even though FillterBO does not mark it required;
    the DigiPay web app always sends it. Omitting it produced the empty-message
    rejection above.
    """
    import inspect

    from tools.v2.txn_ops import get_txn_logs

    default = inspect.signature(get_txn_logs).parameters["type"].default
    assert default not in (None, inspect.Parameter.empty), (
        "`type` must have a concrete default or /v2/txn/logs rejects the call"
    )


# --------------------------------------------------------------------------- #
# Stage dispatch
# --------------------------------------------------------------------------- #

class _Provider(BaseLLMProvider):
    async def generate(self, prompt: str, system_instruction: str = "") -> str:
        return self._simulate_response(prompt, system_instruction)


def test_payload_text_cannot_hijack_the_response_stage():
    """
    The regression: a formatting prompt containing base64 with "dag" in it was
    answered by the planner, returning planner JSON to the user.
    """
    provider = _Provider()
    hostile = "ZGFnZ2VyIHBsYW5uZXIgZGVjb21wb3NlIGRhZw=="  # decodes to text with "dag"
    prompt = (
        'Merchant Query: "Show my passbook for this month"\n'
        f"Backend Tool Outcomes:\n[{{'tool': 'getLedgerPassbookV2', 'result': '{hostile}'}}]\n"
        "<<<VERIFIED_RESULT>>>\n**Ledger passbook**\n\n2 records in total.\n"
        "<<<END_VERIFIED_RESULT>>>"
    )

    out = provider._simulate_response(prompt, system_instruction="Response Formatter")

    assert "planner_confidence" not in out, "planner JSON leaked into a user reply"
    assert "steps" not in out
    assert "Ledger passbook" in out


@pytest.mark.parametrize("instruction,expect_json_keys", [
    ("DAG Planner", ("planner_confidence", "steps")),
    ("Intent Classifier Node", ("intent", "confidence", "tool_calls")),
])
def test_stage_is_chosen_by_system_instruction(instruction, expect_json_keys):
    provider = _Provider()
    prompt = 'User Query: "what is my wallet balance"\nContext merchantId (csc_id): "500100100014"'
    out = provider._simulate_response(prompt, system_instruction=instruction)
    parsed = json.loads(out)
    for key in expect_json_keys:
        assert key in parsed


def test_formatting_stage_returns_the_verified_text():
    provider = _Provider()
    prompt = (
        "Backend Tool Outcomes:\n[]\n"
        "<<<VERIFIED_RESULT>>>\n**Wallet balance**\n\n- **Balance:** Rs 4,560.50\n"
        "<<<END_VERIFIED_RESULT>>>"
    )
    out = provider._simulate_response(prompt, system_instruction="Response Formatter")
    assert "Wallet balance" in out
    assert "4,560.50" in out
