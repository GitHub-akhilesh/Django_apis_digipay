"""
Tests for the DigiPay gateway-service (Spring Boot) chat integration.

Covers the read-only allow-list, CommonResponseBO handling, FillterBO validation,
role-scoped catalogue generation, the message catalogue, tenant isolation, an
end-to-end chat turn against a mocked gateway, and that the pre-existing DigiPay
tools still talk to their original endpoints with their original envelope.
"""

import json

import pytest

from agent.orchestrator import AgentOrchestrator
from core.exceptions import AuthenticationException, GatewayException, ValidationException
from gateway.client import GatewayClient
from gateway.v2.base import GatewayV2Client
from gateway.v2.filters import build_filter
from gateway.v2.safety import ALLOWED_ENDPOINTS, EXCLUDED_ENDPOINTS, resolve_endpoint
from memory.session import session_metadata_memory
from messaging.tool_messages import TOOL_MESSAGES, get_message
from services.tool_executor import tool_executor_service
from tools.catalog import build_tool_catalog, catalog_summary, visible_tools
from tools.decorator import SOURCE_GATEWAY_V2
from tools.registry import TOOL_REGISTRY


# --------------------------------------------------------------------------- #
# Mock Spring Boot gateway
# --------------------------------------------------------------------------- #

class MockResponse:
    def __init__(self, status_code, body=None):
        self.status_code = status_code
        self._body = body if body is not None else {}
        self.text = json.dumps(self._body)

    def json(self):
        return self._body


def common_response(res_data, status="OK", msg="SUCCESS", errors=None):
    """A `com.digipay.common.bos.CommonResponseBO` payload."""
    return {"status": status, "msg": msg, "errors": errors or [], "resData": res_data}


TXN_LOG_PAGE = {
    "totalRecords": 42,
    "list": [
        {"txnDate": "28-07-2026", "txnId": "AEP778812", "type": "AEPS_CASH_WITHDRAWAL",
         "amount": 2000.0, "status": "SUCCESS", "rrn": "512345678901"},
        {"txnDate": "27-07-2026", "txnId": "PAY221190", "type": "PAYOUT",
         "amount": 15000.75, "status": "FAILED", "rrn": None},
    ],
}


@pytest.fixture
def mock_gateway(monkeypatch):
    """Route v2 paths to CommonResponseBO and legacy paths to the {success,data} envelope."""
    calls = []

    async def _request(method, endpoint_path, **kwargs):
        calls.append({"method": method, "path": endpoint_path, **kwargs})

        # ---- Spring gateway-service (CommonResponseBO) ----
        if endpoint_path.startswith("/v2/") or endpoint_path.startswith("/api/v2") \
                or endpoint_path.startswith("/v1/upi"):
            if endpoint_path == "/v2/txn/logs":
                return MockResponse(200, common_response(TXN_LOG_PAGE))
            if endpoint_path == "/v2/ledger/balance":
                return MockResponse(200, common_response(
                    {"cscId": "500100100014", "balance": 4560.50, "blockedAmount": 120.0}))
            if endpoint_path.startswith("/v2/payout/status/"):
                return MockResponse(200, common_response(
                    {"txnId": endpoint_path.rsplit("/", 1)[-1], "status": "PROCESSED",
                     "amount": 4560.50, "mode": "IMPS", "utr": "IMPS2026072188921"}))
            if endpoint_path == "/v2/notification/fetch":
                return MockResponse(200, common_response({"list": []}))
            if endpoint_path == "/v1/upi/vpa/suggestion":
                return MockResponse(200, common_response(["vle.test@digipay"]))
            if endpoint_path == "/v2/device/list":
                return MockResponse(200, common_response(
                    {"list": [{"deviceType": "FINGERPRINT", "deviceModel": "Mantra MFS100",
                               "status": "ACTIVE"}]}))
            return MockResponse(200, common_response({}))

        # ---- Pre-existing DigiPay APIs ({success, data}) ----
        if "transaction" in endpoint_path:
            return MockResponse(200, {"success": True, "message": "Success", "data": {
                "txnId": "123", "amount": 1000.0, "status": "REVERSED",
                "merchantId": "500100100014", "timestamp": "2026-07-20T18:00:00Z"}})
        return MockResponse(200, {"success": True, "message": "Success",
                                  "data": {"balance": 4560.50, "currency": "INR"}})

    monkeypatch.setattr(GatewayClient, "request", _request)
    return calls


# --------------------------------------------------------------------------- #
# 1. Read-only enforcement
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("method,path", [
    ("POST", "/v2/ledger/deposit"),
    ("POST", "/v2/ledger/withdrawal"),
    ("POST", "/v2/ledger/transfer"),
    ("POST", "/v2/aeps/cash-withdrawal"),
    ("POST", "/v2/aeps/cash-deposit"),
    ("POST", "/v2/aeps/reqotp"),
    ("POST", "/v2/payout/init"),
    ("POST", "/v2/payout/admin/refund"),
    ("POST", "/v2/dsptopup/init"),
    ("POST", "/v2/admin/block"),
    ("POST", "/v2/device/register"),
    ("POST", "/v2/device/deregister"),
    ("POST", "/v2/notification/create"),
    ("POST", "/v2/notification/delete"),
    ("POST", "/v2/operator/action"),
    ("POST", "/v2/aua/bio-auth"),
    ("POST", "/v2/user/validate-otp"),
    ("POST", "/v2/user/generate-otp"),
    ("POST", "/v1/upi/refund"),
    ("POST", "/v1/upi/merchant/onboarding"),
    ("POST", "/v2/vatm/transactions"),
    ("POST", "/api/thirdparty/credit/process"),
    ("POST", "/v2/api/client/vle/block"),
])
def test_mutating_endpoints_are_blocked(method, path):
    """Money movement, writes and authentication must be unreachable."""
    with pytest.raises(AuthenticationException) as exc:
        resolve_endpoint(method, path)
    assert "Blocked" in str(exc.value.developer_message)


def test_unlisted_endpoint_is_blocked():
    with pytest.raises(AuthenticationException) as exc:
        resolve_endpoint("POST", "/v2/something/invented")
    assert "not on the read-only gateway allow-list" in str(exc.value.developer_message)


def test_templated_allowed_paths_resolve():
    assert resolve_endpoint("GET", "/v2/admin/details/500100100014")
    assert resolve_endpoint("GET", "/v2/payout/status/PAY99").controller == "PayOutController"
    assert resolve_endpoint("GET", "/v2/operator/list/500100100014")
    assert resolve_endpoint("POST", "/v2/txn/logs").controller == "TxnLogController"


def test_allow_list_and_exclusions_do_not_overlap():
    """A path may not be simultaneously callable and excluded."""
    overlaps = [
        spec.key
        for spec in ALLOWED_ENDPOINTS
        for method, path, _, _ in EXCLUDED_ENDPOINTS
        if spec.matches(method, path)
    ]
    assert overlaps == []


@pytest.mark.anyio
async def test_v2_client_refuses_before_any_network_call(monkeypatch):
    """Enforcement happens before a socket is opened."""
    called = []

    async def _should_not_run(*args, **kwargs):
        called.append(1)
        return MockResponse(200, common_response({}))

    monkeypatch.setattr(GatewayClient, "request", _should_not_run)

    with pytest.raises(AuthenticationException):
        await GatewayV2Client.call(
            method="POST", path="/v2/ledger/transfer", service="ledger", operation="transfer"
        )
    assert called == []


def test_every_gateway_tool_is_read_only():
    """No tool backed by the gateway may be registered as state-changing."""
    offenders = [
        meta.name for meta in TOOL_REGISTRY.values()
        if meta.source == SOURCE_GATEWAY_V2 and not meta.read_only
    ]
    assert offenders == []


def test_every_gateway_tool_endpoint_is_allow_listed():
    """Each gateway tool's declared endpoint must resolve against the allow-list."""
    for meta in TOOL_REGISTRY.values():
        if meta.source != SOURCE_GATEWAY_V2:
            continue
        assert meta.endpoint, f"{meta.name} declares no endpoint"
        method, path = meta.endpoint.split(" ", 1)
        # Substitute the path template with a concrete value.
        concrete = path.replace("{cscId}", "500100100014").replace("{txnId}", "TXN123")
        assert resolve_endpoint(method, concrete), f"{meta.name} -> {meta.endpoint}"


# --------------------------------------------------------------------------- #
# 2. CommonResponseBO envelope
# --------------------------------------------------------------------------- #

@pytest.mark.anyio
async def test_common_response_ok_is_unwrapped(mock_gateway):
    data = await GatewayV2Client.call(
        method="POST", path="/v2/txn/logs", service="txn", operation="txnLogs",
        json_data={"cscId": "500100100014"},
    )
    assert data["totalRecords"] == 42
    assert len(data["list"]) == 2


@pytest.mark.anyio
async def test_common_response_err_becomes_gateway_exception(monkeypatch):
    async def _request(method, endpoint_path, **kwargs):
        return MockResponse(200, common_response(None, status="ERR", msg="Ledger service down"))

    monkeypatch.setattr(GatewayClient, "request", _request)

    with pytest.raises(GatewayException) as exc:
        await GatewayV2Client.call(
            method="POST", path="/v2/txn/logs", service="txn", operation="txnLogs"
        )
    assert "Ledger service down" in str(exc.value.developer_message)


@pytest.mark.anyio
async def test_common_response_validation_errors_are_surfaced(monkeypatch):
    async def _request(method, endpoint_path, **kwargs):
        return MockResponse(200, common_response(
            None, status="VAR", msg="VALIDATION_ERRORS",
            errors=[{"field": "cscId", "message": "'cscId' length must be 12."}]))

    monkeypatch.setattr(GatewayClient, "request", _request)

    with pytest.raises(GatewayException) as exc:
        await GatewayV2Client.call(
            method="POST", path="/v2/txn/logs", service="txn", operation="txnLogs"
        )
    message = str(exc.value.developer_message)
    assert "cscId" in message and "length must be 12" in message


@pytest.mark.anyio
async def test_none_valued_filters_are_not_sent(mock_gateway):
    """Unset filters must be omitted so Spring validators only see real fields."""
    await GatewayV2Client.call(
        method="POST", path="/v2/txn/logs", service="txn", operation="txnLogs",
        json_data={"cscId": "500100100014", "status": None, "rrn": None},
    )
    sent = mock_gateway[-1]["json_data"]
    assert sent == {"cscId": "500100100014"}


# --------------------------------------------------------------------------- #
# 3. FillterBO construction
# --------------------------------------------------------------------------- #

def test_filter_rejects_short_csc_id():
    with pytest.raises(ValidationException):
        build_filter(csc_id="12345", require_csc=True)


def test_filter_requires_csc_when_mandatory():
    with pytest.raises(ValidationException):
        build_filter(require_csc=True)


def test_filter_normalises_iso_dates_to_gateway_format():
    payload = build_filter(csc_id="500100100014", from_date="2026-07-01", to_date="31-07-2026")
    assert payload["fromDate"] == "01-07-2026"
    assert payload["toDate"] == "31-07-2026"


def test_filter_rejects_unparseable_date():
    with pytest.raises(ValidationException):
        build_filter(from_date="last tuesday")


def test_filter_clamps_page_size_and_omits_unset_fields():
    payload = build_filter(csc_id="500100100014", rpp=5000, cp=3)
    assert payload["rpp"] == 50
    assert payload["cp"] == 3
    assert "rrn" not in payload and "utr" not in payload


def test_filter_rejects_non_positive_pagination():
    with pytest.raises(ValidationException):
        build_filter(cp=0)
    with pytest.raises(ValidationException):
        build_filter(rpp=0)


# --------------------------------------------------------------------------- #
# 4. Catalogue and message coverage
# --------------------------------------------------------------------------- #

def test_gateway_tools_are_registered():
    summary = catalog_summary()
    assert summary["bySource"].get(SOURCE_GATEWAY_V2, 0) >= 30
    # The pre-existing tools must still be present.
    for legacy in ("getWalletBalance", "getLimits", "getMerchantProfile", "getTransaction",
                   "reverseTransaction", "raiseTicket", "balanceEnquiry", "getPayoutStatus"):
        assert legacy in TOOL_REGISTRY, f"legacy tool {legacy} disappeared"


def test_catalog_is_role_scoped():
    merchant = {m.name for m in visible_tools(roles=["ROLE_MERCHANT"])}
    admin = {m.name for m in visible_tools(roles=["ROLE_ADMIN"])}

    assert "adminGetUserList" in admin
    assert "adminGetUserList" not in merchant
    assert "getTxnLogs" in merchant and "getTxnLogs" in admin

    catalog = build_tool_catalog(roles=["ROLE_MERCHANT"])
    assert "adminGetUserList" not in catalog
    assert "getTxnLogs" in catalog


def test_catalog_text_does_not_shadow_caller_context():
    """
    The offline simulator scrapes `cscId:` / `txnId:` patterns out of the prompt.
    The catalogue must never emit an argument name followed by ':' or '='.
    """
    import re
    catalog = build_tool_catalog(include_examples=True)
    assert not re.search(r'\b(csc_?id|txn_?id|merchant_?id)\s*[:=]', catalog, re.IGNORECASE)


def test_catalog_exposes_required_and_optional_args():
    txn_logs = TOOL_REGISTRY["getTxnLogs"]
    assert txn_logs.required_args == ["cscId"]
    assert "fromDate" in txn_logs.optional_args and "rpp" in txn_logs.optional_args
    # jwt_token is transport plumbing, never an LLM-visible argument.
    assert "jwtToken" not in txn_logs.arg_names


def test_every_gateway_tool_has_chat_wording():
    missing = [
        meta.name for meta in TOOL_REGISTRY.values()
        if meta.source == SOURCE_GATEWAY_V2 and meta.name not in TOOL_MESSAGES
    ]
    assert missing == [], f"tools without a message catalogue entry: {missing}"


def test_admin_tools_have_role_specific_denial_wording():
    denied = get_message("adminGetUserList").denied
    assert "administrator" in denied.lower()


def test_message_catalogue_has_no_stale_entries():
    """Wording for a tool that no longer exists is misleading documentation."""
    stale = [name for name in TOOL_MESSAGES if name not in TOOL_REGISTRY]
    assert stale == [], f"message entries with no registered tool: {stale}"


def test_every_allow_listed_endpoint_is_reachable_through_a_tool():
    """An allow-listed endpoint with no tool is dead surface area."""
    declared = {meta.endpoint for meta in TOOL_REGISTRY.values() if meta.endpoint}
    orphans = [spec.key for spec in ALLOWED_ENDPOINTS if spec.key not in declared]
    assert orphans == [], f"allow-listed endpoints with no tool: {orphans}"


def test_no_tool_grants_broader_roles_than_its_endpoint():
    """A tool must not widen access beyond what the allow-list entry permits."""
    spec_by_key = {spec.key: spec for spec in ALLOWED_ENDPOINTS}
    widened = []
    for meta in TOOL_REGISTRY.values():
        if meta.source != SOURCE_GATEWAY_V2:
            continue
        spec = spec_by_key.get(meta.endpoint)
        if spec and set(meta.roles) - set(spec.roles):
            widened.append((meta.name, sorted(set(meta.roles) - set(spec.roles))))
    assert widened == [], f"tools broader than their endpoint: {widened}"


# --------------------------------------------------------------------------- #
# 5. Rendering
# --------------------------------------------------------------------------- #

def test_paginated_result_renders_a_table_with_totals():
    from messaging.formatter import message_formatter

    out = message_formatter.render("getTxnLogs", TXN_LOG_PAGE)
    assert "| Date | Txn ID | Service | Amount | Status | RRN |" in out
    assert "₹2,000.00" in out and "₹15,000.75" in out
    # Range, page number and the phrase to type for the next page.
    assert "Showing 1–2 of 42" in out
    assert "page 1 of 21" in out
    assert "“page 2”" in out
    assert "—" in out  # the null RRN renders as a dash, not "None"


def test_unmatched_payload_columns_are_still_shown():
    """
    A partial column match used to stop the search: the ledger passbook declared
    six columns, the live payload populated only two, and the table rendered as
    "Date | Narration" — hiding the amount and running balance that were present
    under different names.
    """
    from messaging.formatter import message_formatter

    payload = {
        "totalRecords": 1,
        "list": [{
            "txnDate": "21-07-2026",
            "remarks": "PAYOUT/ RRN: 784997725519",
            # Present in the real response, absent from the declared columns:
            "someUnexpectedAmount": 1500.0,
            "unmappedStatus": "SUCCESS",
        }],
    }
    out = message_formatter.render("getLedgerPassbookV2", payload)
    assert "Some Unexpected Amount" in out
    assert "Unmapped Status" in out
    assert "SUCCESS" in out


def test_empty_result_uses_the_empty_message_not_an_empty_table():
    from messaging.formatter import message_formatter

    out = message_formatter.render("getNotifications", {"list": []})
    assert "no notifications" in out.lower()
    assert "|" not in out


def test_sensitive_fields_are_never_rendered():
    from messaging.formatter import message_formatter

    out = message_formatter.render("getAuaAuthStatus", {
        "txnId": "AUA1", "status": "SUCCESS",
        "aadhaarNumber": "123456789012", "pidData": "BASE64", "otp": "445566",
    })
    assert "123456789012" not in out
    assert "BASE64" not in out
    assert "445566" not in out


def test_unknown_payload_shape_still_renders():
    from messaging.formatter import message_formatter

    out = message_formatter.render("adminGetReport", {"unmappedField": "abc", "tally": 7})
    assert "Unmapped Field" in out and "abc" in out


# --------------------------------------------------------------------------- #
# 5b. PII redaction must not destroy operational identifiers
# --------------------------------------------------------------------------- #

def test_labelled_identifiers_survive_redaction():
    """
    An RRN, a UTR and a CSC ID are all 12 digits, like an Aadhaar number. They are
    exactly what a merchant needs to raise a bank dispute, so they must stay
    readable.
    """
    from workflow.nodes.respond import mask_pii

    for line in ("- **RRN:** 512345678901",
                 "- **UTR:** 226789012345",
                 "- **CSC ID:** 500100100014",
                 "- **Txn ID:** 787654321012",
                 "- **Reference:** 512345678901"):
        assert mask_pii(line) == line, f"redaction mangled: {line}"


def test_identifier_table_columns_survive_redaction():
    from workflow.nodes.respond import mask_pii

    table = (
        "| Date | Txn ID | Status | RRN |\n"
        "| --- | --- | --- | --- |\n"
        "| 28-07-2026 | 226789012345 | SUCCESS | 512345678901 |\n"
    )
    out = mask_pii(table)
    assert "512345678901" in out
    assert "226789012345" in out


def test_aadhaar_and_mobile_are_still_redacted():
    from workflow.nodes.respond import mask_pii

    out = mask_pii("Customer Aadhaar 987654321012 verified. Call the VLE on 9876543210.")
    assert "987654321012" not in out
    assert "9876543210" not in out
    assert "XXXX XXXX 1012" in out

    # An Aadhaar-headed table column must still be redacted.
    table = "| Name | Aadhaar |\n| --- | --- |\n| Ramesh | 234567890123 |\n"
    assert "234567890123" not in mask_pii(table)


def test_amounts_are_not_mistaken_for_phone_numbers():
    from workflow.nodes.respond import mask_pii

    # Indian mobiles start 6-9; a 10-digit value starting 1 is not a phone number.
    assert mask_pii("Amount credited: 1500000000") == "Amount credited: 1500000000"


# --------------------------------------------------------------------------- #
# 6. Tenant isolation
# --------------------------------------------------------------------------- #

@pytest.mark.anyio
async def test_merchant_cannot_read_another_csc_id(mock_gateway):
    with pytest.raises(AuthenticationException) as exc:
        await tool_executor_service.execute_tool(
            tool_name="getTxnLogs",
            args={"cscId": "500100100015"},
            user_roles=["ROLE_MERCHANT"],
            caller_merchant_id="500100100014",
        )
    assert "Tenant Isolation Breach" in str(exc.value.developer_message)


@pytest.mark.anyio
async def test_merchant_can_read_own_csc_id(mock_gateway):
    res = await tool_executor_service.execute_tool(
        tool_name="getTxnLogs",
        args={"cscId": "500100100014"},
        user_roles=["ROLE_MERCHANT"],
        caller_merchant_id="500100100014",
    )
    assert res["result"]["totalRecords"] == 42
    assert "Transaction log" in res["message"]


@pytest.mark.anyio
async def test_admin_may_read_another_csc_id(mock_gateway):
    """Admin reports exist to inspect other users; RBAC still gates which tools."""
    res = await tool_executor_service.execute_tool(
        tool_name="adminGetDailyTxnReport",
        args={"cscId": "500100100015"},
        user_roles=["ROLE_ADMIN"],
        caller_merchant_id="500100100014",
    )
    assert res["result"] is not None


@pytest.mark.anyio
async def test_merchant_is_refused_an_admin_tool(mock_gateway):
    with pytest.raises(AuthenticationException) as exc:
        await tool_executor_service.execute_tool(
            tool_name="adminGetUserList",
            args={},
            user_roles=["ROLE_MERCHANT"],
            caller_merchant_id="500100100014",
        )
    assert "lack permission" in str(exc.value.developer_message)


# --------------------------------------------------------------------------- #
# 7. End-to-end chat turns
# --------------------------------------------------------------------------- #

@pytest.mark.anyio
async def test_named_service_uses_the_per_service_txn_log(mock_gateway):
    """
    /v2/txn/logs is per-Category and rejects a call without a valid one, so it is
    used only when the user names a service — and the Category must be sent.
    """
    session_metadata_memory.save_metadata("session_v2_txn", {})

    res = await AgentOrchestrator.chat(
        session_id="session_v2_txn",
        message="show my aeps cash withdrawal logs for this month",
        csc_id="500100100014",
        history=[],
        user_roles=["ROLE_MERCHANT"],
    )

    assert res["intent"] == "TXN_HISTORY"
    assert "getTxnLogs" in res["explainability"]["selectedTools"]
    call = next(c for c in mock_gateway if c["path"] == "/v2/txn/logs")
    assert call["json_data"]["type"] == "AEPS_CASH_WITHDRAWAL", (
        "the gateway rejects /v2/txn/logs without a valid Category"
    )
    assert res["escalate"] is False


@pytest.mark.anyio
async def test_generic_history_uses_the_passbook(mock_gateway):
    """
    "show my transaction history" names no service, and there is no "ALL"
    Category, so it must go to the ledger passbook — which is genuinely
    cross-service and returns real rows.
    """
    session_metadata_memory.save_metadata("session_v2_generic", {})

    res = await AgentOrchestrator.chat(
        session_id="session_v2_generic",
        message="show my transaction history for this month",
        csc_id="500100100014",
        history=[],
        user_roles=["ROLE_MERCHANT"],
    )

    assert "getLedgerPassbookV2" in res["explainability"]["selectedTools"]
    assert any(c["path"] == "/v2/ledger/passbook" for c in mock_gateway)
    assert not any(c["path"] == "/v2/txn/logs" for c in mock_gateway)
    assert res["escalate"] is False


@pytest.mark.anyio
async def test_page_request_is_honoured(mock_gateway):
    """
    The reply tells the user to say "page 3", so that has to actually page.
    """
    session_metadata_memory.save_metadata("session_v2_page", {})

    await AgentOrchestrator.chat(
        session_id="session_v2_page",
        message="show my passbook page 3",
        csc_id="500100100014",
        history=[],
        user_roles=["ROLE_MERCHANT"],
    )

    call = next(c for c in mock_gateway if c["path"] == "/v2/ledger/passbook")
    assert call["json_data"]["cp"] == 3


@pytest.mark.anyio
async def test_chat_turn_refuses_money_movement(mock_gateway):
    session_metadata_memory.save_metadata("session_v2_block", {})

    res = await AgentOrchestrator.chat(
        session_id="session_v2_block",
        message="please transfer money from my wallet to 500100100099",
        csc_id="500100100014",
        history=[],
        user_roles=["ROLE_MERCHANT"],
    )

    assert res["intent"] == "UNSUPPORTED_ACTION"
    assert "read-only" in res["response"]
    # No gateway call may have been attempted at all.
    assert mock_gateway == []


@pytest.mark.anyio
async def test_chat_turn_lists_capabilities_from_the_registry(mock_gateway):
    session_metadata_memory.save_metadata("session_v2_caps", {})

    res = await AgentOrchestrator.chat(
        session_id="session_v2_caps",
        message="what can you do for me?",
        csc_id="500100100014",
        history=[],
        user_roles=["ROLE_MERCHANT"],
    )

    assert res["intent"] == "CAPABILITIES"
    response = res["response"]

    # Phrased for a user, not a developer: the reply offers example questions, so
    # internal tool names and argument lists must not appear. The prompt catalogue
    # ("getTxnLogs, optional args -> cscId, ...") is for the model only.
    assert "getTxnLogs" not in response
    assert "adminGetUserList" not in response
    assert "optional args" not in response

    # It must still be generated from the live registry, not a static blurb -
    # these example phrasings come from the registered tools' metadata.
    assert "transaction" in response.lower()
    assert "ask me" in response.lower()

    # Role scoping still holds: a merchant sees no administration section.
    assert "Administration" not in response


@pytest.mark.anyio
async def test_chat_reply_carries_the_real_gateway_figures(mock_gateway):
    """
    The reply must contain the gateway's actual values, rendered through the
    message catalogue — not a generic acknowledgement.
    """
    session_metadata_memory.save_metadata("session_v2_figures", {})

    res = await AgentOrchestrator.chat(
        session_id="session_v2_figures",
        message="show my aeps cash withdrawal logs",
        csc_id="500100100014",
        history=[],
        user_roles=["ROLE_MERCHANT"],
    )
    response = res["response"]

    assert "₹2,000.00" in response
    assert "₹15,000.75" in response
    assert "AEP778812" in response
    # Pagination states the range and how to reach the next page, because
    # "ask for the next page" alone left the user guessing what to type.
    assert "Showing 1–2 of 42" in response
    assert "page 2" in response
    # The RRN must survive PII redaction — it is a 12-digit number like an Aadhaar.
    assert "512345678901" in response


@pytest.mark.anyio
async def test_chat_turn_explains_a_role_denial_instead_of_escalating(mock_gateway):
    """
    A merchant asking for an admin report must be told plainly that their role
    lacks access — not handed a generic "escalated to Level-2 support" message.
    """
    session_metadata_memory.save_metadata("session_v2_denied", {})

    res = await AgentOrchestrator.chat(
        session_id="session_v2_denied",
        message="show the block history for 500100100099",
        csc_id="500100100014",
        history=[],
        user_roles=["ROLE_MERCHANT"],
    )

    assert res["escalate"] is False
    assert "administrator" in res["response"].lower()
    assert "Level-2" not in res["response"]
    assert mock_gateway == []


@pytest.mark.anyio
async def test_chat_turn_blocks_a_plan_targeting_another_csc_id(monkeypatch, mock_gateway):
    """
    Graph-level proof of the tenant boundary: even if the planner emits a step
    aimed at another CSC ID, execution is stopped and the user is told why.
    """
    from planner.service import PlannerService

    async def _foreign_plan(message, intent, csc_id, user_roles=None):
        return {
            "planner_confidence": 0.99,
            "steps": [{
                "id": "step_1",
                "tool": "getLedgerBalanceV2",
                "args": {"cscId": "500100100099"},   # not the caller
                "dependencies": [],
                "parallel": True,
                "requires_confirmation": False,
            }],
        }

    monkeypatch.setattr(PlannerService, "create_plan", _foreign_plan)
    session_metadata_memory.save_metadata("session_v2_tenant", {})

    res = await AgentOrchestrator.chat(
        session_id="session_v2_tenant",
        message="show me the ledger balance for 500100100099",
        csc_id="500100100014",
        history=[],
        user_roles=["ROLE_MERCHANT"],
    )

    assert "own" in res["response"].lower()
    assert "500100100099" not in res["response"]
    # The gateway must never have been contacted for the foreign record.
    assert not any("/v2/ledger/balance" in c["path"] for c in mock_gateway)


@pytest.mark.anyio
async def test_chat_turn_reads_device_registration(mock_gateway):
    session_metadata_memory.save_metadata("session_v2_dev", {})

    res = await AgentOrchestrator.chat(
        session_id="session_v2_dev",
        message="is my registered device active?",
        csc_id="500100100014",
        history=[],
        user_roles=["ROLE_MERCHANT"],
    )

    assert res["intent"] == "DEVICE_LIST"
    assert any(c["path"] == "/v2/device/list" for c in mock_gateway)


# --------------------------------------------------------------------------- #
# 8. Pre-existing DigiPay integrations are untouched
# --------------------------------------------------------------------------- #

@pytest.mark.anyio
async def test_legacy_wallet_tool_still_uses_its_original_endpoint(mock_gateway):
    res = await tool_executor_service.execute_tool(
        tool_name="getWalletBalance",
        args={"merchantId": "500100100014"},
        user_roles=["ROLE_MERCHANT"],
        caller_merchant_id="500100100014",
    )
    assert res["result"]["balance"] == 4560.50
    assert any(c["path"] == "/wallet/balance" for c in mock_gateway)
    # The legacy client must not be routed through the v2 prefixes.
    assert not any(c["path"].startswith("/v2/") for c in mock_gateway)


@pytest.mark.anyio
async def test_legacy_reversal_still_requires_confirmation(mock_gateway):
    session_metadata_memory.save_metadata("session_v2_rev", {})

    res = await AgentOrchestrator.chat(
        session_id="session_v2_rev",
        message="Please process reversal for transaction 123",
        csc_id="500100100014",
        history=[],
        user_roles=["ROLE_SUPPORT"],
    )
    assert "confirm" in res["response"].lower()

    meta = session_metadata_memory.get_metadata("session_v2_rev")
    assert meta["awaiting_confirmation"] is True


def test_state_changing_legacy_tools_are_flagged():
    """The registry must describe the pre-existing write tools accurately."""
    for name in ("reverseTransaction", "sendAlert", "raiseTicket"):
        assert TOOL_REGISTRY[name].read_only is False, f"{name} should be marked state-changing"


def test_legacy_tools_discovered_by_autodiscovery():
    """
    Regression guard for the module-name bug in tools.discovery: stripping ".py"
    with str.rstrip removed any trailing '.', 'p' or 'y', so
    tools/aeps/balance_enquiry.py never imported and balanceEnquiry never registered.
    """
    import importlib
    import sys

    for module in ("tools.aeps.balance_enquiry", "tools.settlement.payout"):
        sys.modules.pop(module, None)

    from tools.discovery import discover_tools
    registry = discover_tools()
    assert "balanceEnquiry" in registry
    assert "getPayoutStatus" in registry
