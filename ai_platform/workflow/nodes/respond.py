import json
import logging
import re
from typing import Any, Dict, List

from llm.orchestrator import llm_orchestrator
from messaging.formatter import message_formatter
from rag.citation_engine import citation_engine
from rag.hybrid_retriever import hybrid_retriever
from services.audit_service import audit_service
from tools.catalog import visible_tools

logger = logging.getLogger("ai_platform.workflow.nodes.respond")

# Delimiters around the verified, pre-rendered result inside the formatting prompt.
# They make the factual boundary unambiguous for the model, and let the offline
# simulator in `llm.provider` return the verified text verbatim instead of a
# generic acknowledgement when it does not recognise the tools involved.
GROUNDED_START = "<<<VERIFIED_RESULT>>>"
GROUNDED_END = "<<<END_VERIFIED_RESULT>>>"

# Reply used when the user asks for something the assistant is deliberately not
# wired to do. The exclusion register in gateway.v2.safety is the source of truth
# for what falls in here.
UNSUPPORTED_ACTION_REPLY = (
    "I can look up and explain your DigiPay data, but I'm not able to carry out that action. "
    "For your protection I have read-only access, so I cannot:\n\n"
    "- transfer, deposit, withdraw or settle money, or start an AePS / payout / top-up transaction\n"
    "- reverse or refund a payment\n"
    "- block or unblock a user or a service\n"
    "- register or deregister a biometric device, or add and modify operators\n"
    "- create, update or delete records such as notifications and UPI merchants\n"
    "- authenticate a customer or generate an OTP\n\n"
    "Please use the DigiPay app or portal for that. In the meantime I can show you the "
    "relevant transaction, balance, passbook, device or audit records — just ask."
)


async def faq_agent_node(state: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("Graph Node: faq_agent")
    last_msg = state["messages"][-1]["content"] if state["messages"] else ""

    # MongoDB-backed retrieval, falling back to the in-memory index when Mongo
    # is unreachable so FAQ answers never hard-fail on a knowledge-store outage.
    chunks = await hybrid_retriever.aretrieve(last_msg, intent=state.get("intent", "FAQ"))

    faq_content = (
        "\n\n".join([f"### {c['source']} (Page {c['page']})\n{c['text']}" for c in chunks])
        if chunks else "No documents matched."
    )

    prompt = f"""
    You are a support agent. Answer the user question based on the retrieved knowledge base document.
    User Question: "{last_msg}"
    Knowledge Base Document:
    {faq_content}

    Provide a concise, helpful, and friendly support response.
    If the document does not cover the question, say so plainly rather than guessing.
    """

    response = await llm_orchestrator.generate(prompt, system_instruction="RAG Support Advisor")
    citations = citation_engine.format_citations(chunks)

    return {
        "response": response + citations
    }


async def response_agent_node(state: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("Graph Node: response_agent (Formatting & PII Redactor)")

    if state.get("awaiting_confirmation"):
        res_text = (
            "I have prepared a plan that requires your confirmation. "
            "Please review the pending steps and reply 'CONFIRM' to execute."
        )
        return {"response": res_text}

    if state["intent"] == "FAQ" and state.get("response"):
        return {"response": mask_pii(state["response"])}

    if state["intent"] == "CAPABILITIES":
        return {"response": _capabilities_reply(state.get("user_roles"))}

    outcomes = state.get("plan_outcomes", [])
    last_msg = state["messages"][-1]["content"] if state["messages"] else ""

    # An unsupported-action intent, or a request that produced no executable plan
    # because the planner refused it, gets the explicit read-only explanation.
    if state["intent"] == "UNSUPPORTED_ACTION":
        return {"response": UNSUPPORTED_ACTION_REPLY}

    if state.get("escalate"):
        res_text = (
            "I encountered an issue verifying your query context or accessing the database details. "
            "I have flagged this for Level-2 human support. A representative will connect with you shortly."
        )
        return {"response": res_text}

    if not outcomes:
        if state["confidence_score"] < 0.6:
            res_text = "I'm not sure how to retrieve that information. Should I escalate this to a live agent?"
            return {"response": res_text}
        res_text = "Hello, I am your DigiPay AI Support Assistant. How can I help you today?"
        return {"response": res_text}

    # Deterministic wording from the per-tool message catalogue. This is both the
    # reply used when the model is unavailable and the grounding handed to the
    # model, so the numbers a user reads always come from the gateway payload
    # rather than from generation.
    grounded = message_formatter.summarise_outcomes(outcomes)

    prompt = f"""
    You are the response formatting agent for DigiPay AI platform.
    Construct a professional, helpful, friendly, and natural support message to the merchant
    based on their original query and the results returned by our backend tools.

    Merchant Query: "{last_msg}"

    Backend Tool Outcomes:
    {json.dumps(_redact_outcomes(outcomes), default=str)}

    A pre-formatted, factually verified version of these results is delimited below. Reuse its
    figures, tables and record counts EXACTLY — never restate a number that does not appear in
    it, and never invent a value that is missing:
    {GROUNDED_START}
    {grounded}
    {GROUNDED_END}

    Ensure the response is structured, clear, and direct. Format cash/rupees cleanly using ₹ symbols.
    If a lookup failed, say so plainly and suggest the next step.
    """

    try:
        response = await llm_orchestrator.generate(prompt, system_instruction="Response Formatter")
    except Exception as e:
        # The catalogue text is a complete answer on its own, so a model outage
        # degrades presentation rather than losing the user's result.
        logger.error(f"Response formatting via LLM failed: {e}. Falling back to message catalogue.")
        response = grounded

    masked_res = mask_pii(response)

    # Audit Trail Logging
    audit_service.record_interaction(
        session_id="graph_session",
        user_query=last_msg,
        intent=state["intent"],
        tools_executed=outcomes,
        llm_response=masked_res,
        csc_id=state["csc_id"],
        roles=state["user_roles"]
    )

    return {"response": masked_res}


def _capabilities_reply(user_roles: Any) -> str:
    """
    Answer "what can you do?" in the user's language, from the live registry.

    Built from each tool's `examples` — the phrasings a person would actually
    type — rather than from the prompt catalogue. That catalogue is written for
    the model: it lists internal tool names and argument lists
    ("getAepsBalanceEnquiryDetails, optional args -> cscId, txnId, rrn"), which is
    meaningless to a VLE and reads as a system dump. Generated, not hard-coded, so
    a newly registered tool appears here automatically.
    """
    tools = visible_tools(roles=user_roles, include_write=False)

    # Domains grouped under headings a user recognises. Unlisted domains are
    # collected under "Other", so nothing silently disappears.
    domain_titles = {
        "ledger": "Your money",
        "legacy": "Older records",
        "transaction": "Your transactions",
        "aeps": "AePS activity",
        "analytics": "Business summary",
        "payout": "Settlements and payouts",
        "device": "Your devices",
        "operator": "Your operators",
        "notification": "Notifications",
        "catalog": "Your services",
        "admin": "Administration",
        "aua": "Aadhaar authentication",
        "upi": "UPI",
        "platform": "Platform details",
    }

    grouped: Dict[str, List[str]] = {}
    for meta in tools:
        if not meta.examples:
            continue
        title = domain_titles.get(meta.domain, "Other")
        # One example per tool keeps the list readable inside a chat bubble.
        grouped.setdefault(title, []).append(meta.examples[0])

    if not grouped:
        return (
            "I can look up your DigiPay records — balances, transactions, passbook, "
            "devices and notifications — and answer questions about DigiPay's rules."
        )

    lines = ["Here are some things you can ask me:", ""]
    for title in [t for t in domain_titles.values() if t in grouped] + (
        ["Other"] if "Other" in grouped else []
    ):
        examples = grouped[title]
        lines.append(f"**{title}**")
        for example in examples[:3]:
            lines.append(f"- “{example}”")
        lines.append("")

    lines.append(
        "I can also explain DigiPay's rules — transaction limits, settlement times, "
        "KYC and chargebacks."
    )
    lines.append("")
    lines.append(
        "_I can look things up and explain them, but I can't move money, reverse a "
        "payment or change your records. Please use the DigiPay app for those._"
    )
    return "\n".join(lines)


def _redact_outcomes(outcomes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Strip the pre-rendered message before handing outcomes to the model — it is
    supplied separately as grounding, and duplicating it wastes prompt budget.
    """
    return [{k: v for k, v in o.items() if k != "message"} for o in outcomes]


# Labels whose value is an operational identifier, not PII. An RRN, a UTR and a
# CSC ID are all 12 digits, so a length-only Aadhaar rule mangled exactly the
# references a merchant needs to raise a bank dispute. These are protected before
# masking runs and restored afterwards.
IDENTIFIER_LABELS = (
    r"rrn|utr|csc\s*id|cscid|merchant\s*id|txn\s*id|txnid|transaction\s*id|"
    r"reference|ref\s*no|refno|serial(?:\s*no)?|ticket\s*id|account\s*(?:no|number)"
)

IDENTIFIER_LABEL_PATTERN = re.compile(
    rf"((?:{IDENTIFIER_LABELS})\W{{0,4}})(\d[\d\s-]{{5,}})",
    re.IGNORECASE,
)

# Same vocabulary, matched against a markdown table header cell. In a rendered
# table the label sits in the header row and the value several lines below, so
# label proximity cannot protect it — the column has to be identified instead.
IDENTIFIER_HEADER_PATTERN = re.compile(rf"^\W*(?:{IDENTIFIER_LABELS})\W*$", re.IGNORECASE)

TABLE_DIVIDER_PATTERN = re.compile(r"^\s*\|(?:\s*:?-{2,}:?\s*\|)+\s*$")

DIGIT_CELL_PATTERN = re.compile(r"^[\d\s-]{6,}$")

# UIDAI never issues an Aadhaar number beginning with 0 or 1, so requiring a
# leading 2-9 removes a large class of false positives on its own.
AADHAAR_PATTERN = re.compile(r"\b([2-9]\d{3})[\s-]?(\d{4})[\s-]?(\d{4})\b")

# Indian mobile numbers begin 6-9. Anchoring on that stops 10-digit amounts and
# reference numbers from being rewritten as phone numbers.
MOBILE_PATTERN = re.compile(r"\b[6-9]\d{6}(\d{3})\b")


def _park_identifier_columns(text: str, protected: List[str]) -> str:
    """
    Park the numeric cells of markdown table columns headed by an identifier
    label (RRN, UTR, Txn ID, CSC ID, …) so masking cannot rewrite them.
    """
    lines = text.split("\n")
    identifier_columns: set = set()
    in_table = False

    for index, line in enumerate(lines):
        if not line.lstrip().startswith("|"):
            in_table = False
            identifier_columns = set()
            continue

        # A header row is the line immediately above the |---|---| divider.
        if index + 1 < len(lines) and TABLE_DIVIDER_PATTERN.match(lines[index + 1]):
            cells = line.split("|")
            identifier_columns = {
                position for position, cell in enumerate(cells)
                if IDENTIFIER_HEADER_PATTERN.match(cell.strip())
            }
            in_table = True
            continue

        if TABLE_DIVIDER_PATTERN.match(line) or not in_table or not identifier_columns:
            continue

        cells = line.split("|")
        for position in identifier_columns:
            if position >= len(cells):
                continue
            value = cells[position].strip()
            if DIGIT_CELL_PATTERN.match(value):
                protected.append(value)
                cells[position] = f" \x00{len(protected) - 1}\x00 "
        lines[index] = "|".join(cells)

    return "\n".join(lines)


def mask_pii(text: str) -> str:
    """
    Redact Aadhaar and mobile numbers while leaving operational identifiers
    (RRN, UTR, CSC ID, transaction and ticket references) readable.

    Redaction is context-aware because it has to be: an Aadhaar number, an RRN,
    a UTR and a CSC ID are all 12 digits, so a length-only rule destroyed exactly
    the references a merchant needs to raise a bank dispute.
    """
    if not text:
        return text

    protected: List[str] = []

    # 1. Park identifiers — both label-adjacent and in identifier table columns.
    text = _park_identifier_columns(text, protected)

    def _park(match):
        protected.append(match.group(2))
        return f"{match.group(1)}\x00{len(protected) - 1}\x00"

    text = IDENTIFIER_LABEL_PATTERN.sub(_park, text)

    # 2. Mask what remains.
    text = AADHAAR_PATTERN.sub(lambda m: f"XXXX XXXX {m.group(3)}", text)
    text = MOBILE_PATTERN.sub(lambda m: f"XXXXXXX{m.group(1)}", text)

    # 3. Restore the parked identifiers.
    for index, value in enumerate(protected):
        text = text.replace(f"\x00{index}\x00", value)

    return text
