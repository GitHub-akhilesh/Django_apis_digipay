import re
import json
import logging
from abc import ABC, abstractmethod
from typing import Optional, Tuple

logger = logging.getLogger("ai_platform.llm.provider")

# ---------------------------------------------------------------------------
# Offline routing table for the gateway-service read APIs.
#
# `_simulate_response` stands in for a real model when no provider key is
# configured, so without entries here the gateway tools would be unreachable in
# local and CI runs. These routes are matched BEFORE the original keyword chains
# below, using phrases distinctive enough not to shadow them.
#
# Each entry is (trigger phrases, intent, tool name, identifier the tool needs).
# ---------------------------------------------------------------------------
GATEWAY_ROUTES: Tuple[Tuple[Tuple[str, ...], str, str, str], ...] = (
    # Legacy DigiPay API service first: "legacy"/"old system" is an explicit
    # request for that system, and must not be answered from the current one.
    (("legacy passbook", "old passbook", "passbook from the old"),
     "LEGACY_PASSBOOK", "getLegacyPassbook", "legacy_range"),
    (("legacy transaction", "legacy txn", "old transaction", "old system transaction",
      "archived transaction"), "LEGACY_TXN_LOGS", "getLegacyTxnLogs", "legacy_logs"),
    (("legacy balance", "legacy wallet", "old wallet balance", "old digipay balance"),
     "LEGACY_WALLET_BALANCE", "getLegacyWalletBalance", "csc"),

    (("passbook",), "LEDGER_PASSBOOK", "getLedgerPassbookV2", "csc"),
    # Balance questions must reach the gateway's ledger endpoint. The
    # pre-existing getWalletBalance tool targets /wallet/balance, which the
    # DigiPay Spring gateway does not serve (401), so routing "wallet balance"
    # to it produced "flagged for Level-2 human support" instead of a figure.
    (("ledger balance", "digipay balance", "wallet balance", "my balance",
      "check my balance", "current balance", "available balance", "balance enquiry",
      "how much balance", "how much money"),
     "LEDGER_BALANCE", "getLedgerBalanceV2", "csc"),
    (("recovery",), "LEDGER_RECOVERY", "getLedgerRecoveryList", "csc"),
    # Analytics BEFORE transaction history: "summarise my transactions this month"
    # contains "my transactions", so the history route would otherwise swallow it
    # and return a raw list where the user asked for a summary.
    (("summarise", "summarize", "summary of my", "analytics", "commission",
      "how much did i earn", "business summary", "total sales"),
     "TXN_ANALYTICS", "getTxnAnalytics", "csc"),
    # A named service goes to the per-service log; anything generic goes to the
    # ledger passbook.
    #
    # /v2/txn/logs is per-Category and rejects a call without a valid one, and
    # there is no "ALL" — so "show my transaction history" could never be answered
    # by it. The passbook IS the user's cross-service history and returns real
    # rows (728 for this account), so generic phrasing routes there instead.
    (("aeps withdrawal", "aeps cash withdrawal", "cash withdrawal", "aeps deposit",
      "cash deposit", "mini statement", "my payouts", "payout log", "payout history",
      "dsp topup", "dsp top-up", "matm", "vatm", "upi withdrawal"),
     "TXN_HISTORY", "getTxnLogs", "csc_typed"),
    (("transaction history", "my transactions", "transaction log", "txn log",
      "recent transactions", "transactions from", "transactions this", "transactions last"),
     "LEDGER_PASSBOOK", "getLedgerPassbookV2", "csc"),
    (("bank response", "switch response", "why did transaction", "why did my transaction"),
     "TXN_RESPONSE", "getTxnResponse", "ref"),
    # "my AePS balance enquiries this month" is a LIST of enquiries; the details
    # route needs a specific txnId/RRN, so the list must be matched first or the
    # bare word "balance" falls through to the wallet-balance route.
    (("aeps balance enquiries", "aeps balance enquiry list", "my balance enquiries",
      "balance enquiry history"),
     "AEPS_HISTORY", "getAepsBalanceEnquiryList", "csc"),
    (("aeps log", "aeps transaction", "aeps history", "aeps withdrawal history"),
     "AEPS_HISTORY", "getAepsLogs", "csc"),
    (("aeps enquiry", "balance enquiry result", "enquiry result"),
     "AEPS_ENQUIRY_RESULT", "getAepsBalanceEnquiryDetails", "csc"),
    (("notification", "alerts for me"), "NOTIFICATION_VIEW", "getNotifications", "csc"),
    (("announcement", "outage", "maintenance notice"), "ANNOUNCEMENTS", "getLoginNotifications", "none"),
    (("operator",), "OPERATOR_LIST", "getOperatorList", "csc"),
    (("my device", "registered device", "device list", "device registration"),
     "DEVICE_LIST", "getDeviceList", "csc"),
    (("which services", "service catalog", "enabled services", "services do i have",
      "services are active", "active services", "my services", "services enabled"),
     "SERVICE_CATALOG", "getServiceCatalog", "none"),
    # "about me" / profile / bank details, from the self-profile endpoint.
    (("about me", "my profile", "profile details", "my details", "my bank",
      "bank details", "bank account", "which bank", "my kyc", "kyc status"),
     "MY_PROFILE", "getMyProfile", "csc"),
    (("payout status", "settlement status"), "PAYOUT_STATUS", "getPayoutStatusV2", "txn"),
    (("top-up status", "topup status", "dsp top-up", "dsp topup"),
     "DSP_TOPUP_STATUS", "getDspTopUpStatus", "txn"),
    (("aadhaar authentication", "aua status", "bio auth status"),
     "AUA_AUTH_STATUS", "getAuaAuthStatus", "txn"),
    (("vpa", "upi handle"), "UPI_VPA_SUGGESTION", "getUpiVpaSuggestions", "none"),
    (("public key",), "PLATFORM_KEY", "getPlatformPublicKey", "none"),
    (("user directory", "user list", "list vles", "search users"),
     "ADMIN_USER_DIRECTORY", "adminGetUserList", "none"),
    (("user details", "vle details"), "ADMIN_USER_DIRECTORY", "adminGetUserDetails", "csc"),
    (("daily transaction report", "daily txn report"), "ADMIN_REPORTS", "adminGetDailyTxnReport", "csc"),
    (("service history",), "ADMIN_REPORTS", "adminGetServiceHistory", "csc"),
    (("login journey",), "ADMIN_AUDIT", "adminGetLoginJourney", "csc"),
    (("block history", "why was.*blocked", "blocked history"), "ADMIN_AUDIT", "adminGetBlockHistory", "csc"),
    (("agent auth",), "ADMIN_AUDIT", "adminGetAgentAuthLogs", "csc"),
    (("timeout", "timed out"), "ADMIN_REPORTS", "adminGetTimeoutTxnList", "csc"),
    (("dsp wallet transfer",), "ADMIN_SETTLEMENT", "adminGetDspWalletTransferLogs", "csc"),
    (("daily settlement",), "ADMIN_SETTLEMENT", "adminGetDspDailySettlement", "csc"),
)

# Phrases asking for an action the assistant is deliberately not wired to do.
# Deliberately excludes "reversal"/"refund", which the original chain below
# routes to the confirmation-gated reverseTransaction flow.
UNSUPPORTED_PHRASES = (
    "transfer money", "send money", "move money", "make a deposit", "do a deposit",
    "initiate payout", "make a payout", "start a payout", "do a top-up", "initiate top-up",
    "block this user", "block user", "unblock user", "register my device", "register device",
    "deregister", "delete notification", "create notification", "add operator",
    "generate otp", "send otp", "authenticate the customer", "deactivate merchant",
    "activate merchant", "generate qr", "cash withdrawal for", "withdraw cash for",
)

CAPABILITY_PHRASES = (
    "what can you do", "what all can you do", "your capabilities", "what do you support",
    "how can you help", "list your features",
)

# Knowledge questions the RAG corpus actually answers (SOPs on settlement,
# chargebacks, KYC, AePS limits, device setup, status interpretation).
#
# Matched FIRST, ahead of the data routes, because a policy question should be
# answered from the SOPs rather than by running a query: "what is the AePS
# transaction limit" wants the limits SOP, not a list of the caller's AePS
# transactions. Phrases are therefore specific rather than broad — "kyc reject"
# is knowledge, while a bare "kyc" remains a status lookup, and "daily limits for
# my wallet" still resolves to getLimits.
#
# Before this table existed, "how long does a chargeback window last" matched
# nothing, fell through to the planner's guess of getMerchantProfile, and surfaced
# as a spurious "escalated to Level-2 support" — with the whole SOP corpus sitting
# unread in MongoDB.
FAQ_PHRASES = (
    # settlement and payouts
    "settlement sla", "settlement cycle", "settlement time", "payout cycle",
    "stuck payout", "stuck payouts", "settle my", "how do i settle", "neft", "imps", "rtgs",
    # disputes
    "chargeback", "dispute window", "dispute rule", "adjustment cycle",
    # kyc
    "kyc approval", "kyc reject", "kyc document", "kyc time", "kyc sla", "verification timeline",
    # devices and biometrics
    "face rd", "rd service", "fingerprint scanner", "otg", "scanner is not working",
    "device not registered", "install the face",
    # limits and conduct
    "transaction limit", "withdrawal limit", "aeps limit", "split charg", "processing fee",
    "charge a fee", "maximum amount",
    # status interpretation
    "what does pending", "pending status", "timeout status", "debited but not paid",
    "reconcil", "difference between rrn", "rrn and utr", "what is an rrn", "what is a utr",
    # generic knowledge framing
    "sop", "standard operating", "policy", "guideline", "how long does", "what is the rule",
)


# Small talk. Distinguished from an unparseable request so a greeting gets a
# greeting, while a request that could not be understood offers escalation.
GREETING_PHRASES = (
    "hello", "hi ", "hi!", "hey", "good morning", "good afternoon", "good evening",
    "namaste", "thanks", "thank you", "bye", "ok", "okay",
)


def _is_greeting(user_msg: str) -> bool:
    stripped = user_msg.strip().rstrip("?!.")
    if stripped in ("hi", "ok", "okay", "hey", "hello"):
        return True
    return len(stripped.split()) <= 4 and any(p in user_msg for p in GREETING_PHRASES)


def _is_faq(user_msg: str) -> bool:
    """
    Whether the message is a knowledge question the SOP corpus covers.

    Checked BEFORE the gateway data routes: "what is the AePS transaction limit"
    is a policy question answered by the limits SOP, not a request to list the
    caller's AePS transactions. Phrases are specific for the same reason —
    "kyc reject" is knowledge, while a bare "kyc" is still a status lookup.
    """
    return any(phrase in user_msg for phrase in FAQ_PHRASES)


def _match_gateway_route(user_msg: str) -> Optional[Tuple[str, str, str]]:
    """First matching gateway route as (intent, tool, arg_kind), else None."""
    for phrases, intent, tool, arg_kind in GATEWAY_ROUTES:
        for phrase in phrases:
            if ".*" in phrase:
                if re.search(phrase, user_msg):
                    return intent, tool, arg_kind
            elif phrase in user_msg:
                return intent, tool, arg_kind
    return None


def _identifier_from_message(user_msg: str, fallback: str) -> str:
    """
    Pull an identifier the user typed in prose, e.g. "payout status for txnId
    PAY99887" or "reference 512345678901".

    The original extraction only matched `txnId:`/`txn_id=` forms scraped from the
    prompt scaffolding, so a plain-English identifier was replaced by a canned
    value — which made local testing of the status lookups meaningless.
    """
    match = re.search(
        r"(?:txn\s*id|txnid|transaction\s*id|reference|ref\s*no|refno|rrn|utr|ticket\s*id)"
        r"\s*(?:is|=|:)?\s*([a-z0-9][a-z0-9_-]{4,})",
        user_msg,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).upper()
    return fallback


def _extract_verified_result(prompt: str) -> Optional[str]:
    """Pull the delimited verified result out of the response-formatting prompt."""
    match = re.search(
        r"<<<VERIFIED_RESULT>>>(.*?)<<<END_VERIFIED_RESULT>>>", prompt, re.DOTALL
    )
    if not match:
        return None
    # The prompt is an indented f-string; strip the common leading whitespace so
    # markdown tables and bullets survive intact.
    lines = [line[4:] if line.startswith("    ") else line
             for line in match.group(1).strip("\n").split("\n")]
    text = "\n".join(lines).strip()
    return text or None


# DigiPay service categories accepted by /v2/txn/logs and /v2/admin/txn-details.
# Taken from com.digipay.common.enums.Category and mirrored by the web app's
# CATEGORY_LABEL map. There is NO "ALL" value: the endpoint is per-category, and
# sending an invented one makes the gateway reject the call with an empty message.
SERVICE_CATEGORIES = (
    (("aeps cash withdrawal", "aeps withdrawal", "cash withdrawal", "aeps payment"),
     "AEPS_CASH_WITHDRAWAL"),
    (("aeps cash deposit", "cash deposit", "aeps deposit"), "AEPS_CASH_DEPOSIT"),
    (("mini statement",), "AEPS_MINI_STATEMENT"),
    (("aeps balance enquiry", "aeps balance enquiries", "balance enquiry"),
     "AEPS_BALANCE_ENQUIRY"),
    (("payout",), "PAYOUT"),
    (("dsp topup", "dsp top-up", "topup", "top-up"), "DSP_TOPUP"),
    (("matm iserveu", "matm isu"), "MATM_ISERVEU"),
    (("matm eureka", "matm csc", "matm"), "MATM_EUREKA"),
    (("vatm",), "VATM_WITHDRAWAL"),
    (("upi cash withdrawal", "upi withdrawal"), "UPI_CASH_WITHDRAWAL"),
)


def _service_category(user_msg: str) -> Optional[str]:
    """Map a named service in the message to its Category enum value."""
    for phrases, category in SERVICE_CATEGORIES:
        for phrase in phrases:
            if phrase in user_msg:
                return category
    return None


def _page_from_message(user_msg: str) -> int:
    """
    Page number the user asked for, so "page 3" / "next page" actually pages.

    The reply advertises "say 'page 3' for the next one", so the request has to be
    honoured or that instruction is a dead end.
    """
    match = re.search(r"\bpage\s*(\d{1,4})\b", user_msg)
    if match:
        return max(1, int(match.group(1)))
    if re.search(r"\b(next page|more|show more|next)\b", user_msg):
        return 2   # a first "next" from page 1
    return 1


def _gateway_args(arg_kind: str, csc_id: str, txn_id: str, user_msg: str = "") -> dict:
    """Arguments for a simulated gateway tool call."""
    page = _page_from_message(user_msg)
    paged = {"cp": page} if page > 1 else {}

    if arg_kind == "csc":
        return {"cscId": csc_id, **paged}
    if arg_kind == "txn":
        return {"txnId": txn_id}
    if arg_kind == "ref":
        return {
            "refNo": txn_id,
            "type": _service_category(user_msg) or "AEPS_CASH_WITHDRAWAL",
            "cscId": csc_id,
        }
    # /v2/txn/logs is per-service and rejects the call without a valid Category,
    # so the service named in the message is required here.
    if arg_kind == "csc_typed":
        return {
            "cscId": csc_id,
            "type": _service_category(user_msg) or "AEPS_CASH_WITHDRAWAL",
            **paged,
        }
    # The legacy service requires an explicit date range (and a service type for
    # its log search), so the simulator supplies a default window. A real model
    # would derive these from the user's wording.
    if arg_kind == "legacy_range":
        return {"cscId": csc_id, "fromDate": "01-01-2026", "toDate": "31-12-2026", **paged}
    if arg_kind == "legacy_logs":
        return {
            "cscId": csc_id,
            "type": _service_category(user_msg) or "AEPS_CASH_WITHDRAWAL",
            "fromDate": "01-01-2026",
            "toDate": "31-12-2026",
            **paged,
        }
    return {}


class BaseLLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, system_instruction: str = "") -> str:
        """Asynchronously invoke the model with context prompts."""
        pass

    def _simulate_response(self, prompt: str, system_instruction: str) -> str:
        prompt_lower = prompt.lower()

        # Which pipeline stage is calling is decided by system_instruction, not by
        # scanning the prompt text.
        #
        # Scanning was actively harmful: the branch below triggers on the substring
        # "dag" anywhere in the prompt, and the response-formatting prompt embeds
        # the backend payload. Gateway endpoints return base64-encoded resData, and
        # arbitrary base64 readily contains "dag" — so a passbook lookup took the
        # planner branch and returned raw planner JSON to the user:
        #
        #   {"planner_confidence": 0.95, "steps": [{"tool": "getLedgerPassbookV2" ...
        #
        # system_instruction is set explicitly at every call site, so it cannot be
        # spoofed by response data.
        stage = (system_instruction or "").strip().lower()
        if stage:
            if "formatter" in stage or "response" in stage:
                return self._simulate_formatting(prompt, prompt_lower)
            if "planner" in stage or "dag" in stage:
                return self._simulate_planner(prompt_lower)
            if "classifier" in stage or "intent" in stage:
                return self._simulate_classifier(prompt_lower)
            if "rag" in stage or "advisor" in stage or "faq" in stage:
                return self._simulate_faq(prompt_lower)
        
        # Fallback when system_instruction is absent: a narrow keyword scan,
        # kept for any caller that does not set it. Deliberately does NOT match
        # on "dag" or "result" - those appear in payload data.
        if "planner" in prompt_lower or "decompose" in prompt_lower:
            return self._simulate_planner(prompt_lower)
        if "classify" in prompt_lower:
            return self._simulate_classifier(prompt_lower)
        if "tool outcomes" in prompt_lower:
            return self._simulate_formatting(prompt, prompt_lower)
        if "faq" in prompt_lower or "sop" in prompt_lower or "knowledge" in prompt_lower:
            return self._simulate_faq(prompt_lower)

        return "Hello, I am your DigiPay AI Support Assistant. How can I help you today?"

    # ------------------------------------------------------------------
    # Per-stage simulators. Split out of a single if/elif chain so each is
    # chosen by system_instruction instead of by scanning the prompt text,
    # which let base64 payload data hijack the wrong branch.
    # ------------------------------------------------------------------

    def _simulate_planner(self, prompt_lower: str) -> str:
        user_msg_match = re.search(r'(?:user message|user query)\s*:\s*["\'](.*?)["\']', prompt_lower)
        user_msg = user_msg_match.group(1) if user_msg_match else prompt_lower
        
        csc_match = re.search(r'(?:csc_id|cscid|merchantid|merchant_id)\s*[:=]\s*["\']?([a-zA-Z0-9_-]+)["\']?', prompt_lower)
        csc_id = csc_match.group(1) if csc_match else "500100100014"
        
        txn_match = re.search(r'(?:txnid|txn_id)\s*[:=]\s*["\']?([a-zA-Z0-9_-]+)["\']?', prompt_lower)
        txn_id = txn_match.group(1).upper() if txn_match else "CZUCW178186672384906DQQOQSU69890796"

        # Prefer an identifier the user actually typed over the canned default.
        txn_id = _identifier_from_message(user_msg, txn_id)

        # A request to act, or a "what can you do" question, produces no plan.
        # The response node answers both from the registry instead.
        if any(p in user_msg for p in UNSUPPORTED_PHRASES) or \
           any(p in user_msg for p in CAPABILITY_PHRASES):
            return json.dumps({"planner_confidence": 0.95, "steps": []})

        # A knowledge question needs no tools at all — intent FAQ routes to the
        # RAG node, so answer from the SOP corpus rather than running a query.
        if _is_faq(user_msg):
            return json.dumps({"planner_confidence": 0.95, "steps": []})

        # Gateway-service read routes are matched before the original chain.
        gateway_route = _match_gateway_route(user_msg)
        if gateway_route:
            _, tool_name, arg_kind = gateway_route
            return json.dumps({
                "planner_confidence": 0.95,
                "steps": [{
                    "id": "step_1",
                    "tool": tool_name,
                    "args": _gateway_args(arg_kind, csc_id, txn_id, user_msg),
                    "dependencies": [],
                    "parallel": True,
                    "requires_confirmation": False
                }]
            })

        steps = []
        if "balance" in user_msg or "wallet" in user_msg:
            steps.append({
                "id": "step_1",
                "tool": "getWalletBalance",
                "args": {"merchantId": csc_id},
                "dependencies": [],
                "parallel": True,
                "requires_confirmation": False
            })
        elif "limits" in user_msg:
            steps.append({
                "id": "step_1",
                "tool": "getLimits",
                "args": {"merchantId": csc_id},
                "dependencies": [],
                "parallel": True,
                "requires_confirmation": False
            })
        elif "kyc" in user_msg:
            steps.append({
                "id": "step_1",
                "tool": "getMerchantStatus",
                "args": {"merchantId": csc_id},
                "dependencies": [],
                "parallel": True,
                "requires_confirmation": False
            })
        elif "reversal" in user_msg or "refund" in user_msg or "reverse" in user_msg:
            steps.append({
                "id": "step_1",
                "tool": "getTransaction",
                "args": {"txnId": txn_id},
                "dependencies": [],
                "parallel": True,
                "requires_confirmation": False
            })
            steps.append({
                "id": "step_2",
                "tool": "reverseTransaction",
                "args": {"txnId": txn_id},
                "dependencies": ["step_1"],
                "parallel": False,
                "requires_confirmation": True
            })
        # No branch matched. Previously this guessed getMerchantProfile, which
        # meant an unrecognised message ran an unrelated tool — and if that
        # call failed, the user was told their request had been escalated to
        # human support. Returning no steps lets the response node greet or ask
        # for clarification instead.
        # High confidence for a greeting (the response node answers it directly);
        # low for a request that matched nothing, so escalation is offered.
        return json.dumps({
            "planner_confidence": 0.98 if (steps or _is_greeting(user_msg)) else 0.4,
            "steps": steps
        })

    def _simulate_classifier(self, prompt_lower: str) -> str:
        user_msg_match = re.search(r'(?:user message|user query)\s*:\s*["\'](.*?)["\']', prompt_lower)
        user_msg = user_msg_match.group(1) if user_msg_match else prompt_lower
        
        csc_match = re.search(r'(?:csc_id|cscid|merchantid|merchant_id)\s*[:=]\s*["\']?([a-zA-Z0-9_-]+)["\']?', prompt_lower)
        csc_id = csc_match.group(1) if csc_match else "500100100014"
        
        # Extract txnId or ticketId if present
        txn_match = re.search(r'(?:txnid|txn_id|ticketid|ticket_id)\s*[:=]\s*["\']?([a-zA-Z0-9_-]+)["\']?', prompt_lower)
        txn_id = txn_match.group(1).upper() if txn_match else "CZUCW178186672384906DQQOQSU69890796"
        
        intent = "General"
        confidence = 0.98
        tool_calls = []

        # Prefer an identifier the user actually typed over the canned default.
        txn_id = _identifier_from_message(user_msg, txn_id)

        # Requests to act, and capability questions, are classified without
        # tool calls so the response node can answer them explicitly.
        if any(p in user_msg for p in UNSUPPORTED_PHRASES):
            return json.dumps({"intent": "UNSUPPORTED_ACTION", "confidence": 0.97, "tool_calls": []})
        if any(p in user_msg for p in CAPABILITY_PHRASES):
            return json.dumps({"intent": "CAPABILITIES", "confidence": 0.97, "tool_calls": []})

        # Knowledge questions answered by the SOP corpus, before any data route.
        if _is_faq(user_msg):
            return json.dumps({"intent": "FAQ", "confidence": 0.96, "tool_calls": []})

        # Gateway-service read routes are matched before the original chain.
        gateway_route = _match_gateway_route(user_msg)
        if gateway_route:
            route_intent, tool_name, arg_kind = gateway_route
            return json.dumps({
                "intent": route_intent,
                "confidence": 0.95,
                "tool_calls": [{
                    "name": tool_name,
                    "args": _gateway_args(arg_kind, csc_id, txn_id, user_msg),
                }],
            })

        # Heuristics based on user_msg
        if "balance" in user_msg or "wallet" in user_msg:
            intent = "Wallet"
            tool_calls.append({"name": "getWalletBalance", "args": {"merchantId": csc_id}})
        elif "limits" in user_msg:
            intent = "Wallet"
            tool_calls.append({"name": "getLimits", "args": {"merchantId": csc_id}})
        elif "kyc" in user_msg:
            intent = "KYC"
            tool_calls.append({"name": "getKYCStatus", "args": {"merchantId": csc_id}})
        elif "bank" in user_msg:
            intent = "KYC"
            tool_calls.append({"name": "getBankAccount", "args": {"merchantId": csc_id}})
        elif "statement" in user_msg:
            intent = "Wallet"
            tool_calls.append({"name": "generateStatement", "args": {"merchantId": csc_id, "fromDate": "2026-06-01", "toDate": "2026-06-30"}})
        elif "reversal" in user_msg or "refund" in user_msg:
            intent = "Refund"
            tool_calls.append({"name": "refundEligibility", "args": {"txnId": txn_id}})
        elif "transaction" in user_msg or "status of" in user_msg:
            intent = "Refund"
            tool_calls.append({"name": "getTransaction", "args": {"txnId": txn_id}})
        elif "close ticket" in user_msg:
            intent = "General"
            tool_calls.append({"name": "closeTicket", "args": {"ticketId": txn_id}})
        elif "ticket" in user_msg or "complain" in user_msg or "dispute" in user_msg:
            intent = "Refund"
            tool_calls.append({"name": "raiseTicket", "args": {"merchantId": csc_id, "category": "Refund", "details": f"Dispute ticket raised"}})
        elif any(k in user_msg for k in ["biometric", "face auth", "fingerprint", "rd service", "limit", "faq"]):
            intent = "FAQ"

        return json.dumps({
            "intent": intent,
            "confidence": confidence,
            "tool_calls": tool_calls
        })

    def _simulate_formatting(self, prompt: str, prompt_lower: str) -> str:
        # We check what tool results are inside the prompt
        if "getwalletbalance" in prompt_lower:
            return "Your wallet balance is ₹4560.50 (Blocked Balance: ₹120.00). Last settlement cleared on 2026-07-19 18:30:00 for ₹1480.00."
        elif "getkycstatus" in prompt_lower:
            return "Your KYC verification status is: APPROVED. Documents: PAN/Aadhaar. Review comments: Documents verified manually."
        elif "getbankaccount" in prompt_lower:
            return "Your registered settlement bank is State Bank of India. Account Number: 30091234567, IFSC: SBIN0001234."
        elif "gettransaction" in prompt_lower:
            if "failed" in prompt_lower:
                return "Transaction CZUCW111222333444555DQQOQSU11122233 of ₹500.00 failed due to: Bank timeout. An automatic reversal has already been initiated and should credit back to the bank account shortly (typically within 20 minutes)."
            return "Transaction CZUCW178186672384906DQQOQSU69890796 of ₹1000.00 was successful on 2026-06-19 16:26:05. UTR: UTR123456789."
        elif "refundeligibility" in prompt_lower:
            if "ineligible" in prompt_lower or "not eligible" in prompt_lower:
                return "Transaction is ineligible for refund. Reason: Transaction status is SUCCESS, not FAILED."
            return "Transaction is eligible for reversal."
        elif "raiseticket" in prompt_lower:
            return "A support ticket has been raised. Our operations team is reviewing it."
        elif "closeticket" in prompt_lower:
            return "Support ticket has been marked CLOSED."
        elif "generatestatement" in prompt_lower:
            return "Your account report is generated: [Download Statement PDF](https://api.digipay.in/statements/stmt_500100100014.pdf)."
        elif "security_blocked" in prompt_lower or "access denied" in prompt_lower:
            return "Security Warning: Access Denied: Record owner mismatch."

        # The formatting prompt carries a pre-rendered, factually verified
        # answer built from the message catalogue. For tools this simulator
        # has no canned copy for — every gateway-service tool — returning that
        # verified text is strictly better than a generic acknowledgement.
        grounded = _extract_verified_result(prompt)
        if grounded:
            return grounded

        return "Your request was processed successfully. All details have been verified."

    def _simulate_faq(self, prompt_lower: str) -> str:
        return ("Based on our SOP Guidelines: Ensure Aadhaar Face RD (v1.1+) is "
                "installed. OTG must be enabled in Settings.")

