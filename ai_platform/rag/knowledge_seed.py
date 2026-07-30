"""
Knowledge documents seeded into the MongoDB RAG store.

Three groups:

1. SOP / policy documents — the operational rules a VLE actually asks about.
   These carry over and expand the content that previously lived inline in
   `rag.retriever.SOP_DATABASE` and `rag.hybrid_retriever.SAMPLE_KNOWLEDGE_DOCS`,
   which are left in place so the in-memory fallback path is unchanged.

2. A capability document generated from the live tool registry, so
   "what can you do?" and "can you check my device registration?" are answered
   from what is actually wired up rather than a hand-written list that rots.

3. A read-only boundary document generated from the gateway allow-list and
   exclusion register, so the assistant can explain *why* it will not perform an
   action and name the correct place to do it.
"""

from typing import Any, Dict, List

SOP_DOCUMENTS: List[Dict[str, Any]] = [
    {
        "source": "Merchant Wallet Payout Settlement SOP.pdf",
        "metadata": {"category": "settlement", "owner": "Operations"},
        "content": """
# Settlement SLA and Payout Cycles
Page 8: Standard settlements are processed daily in batch cycles. IMPS cycles complete within
2 hours. NEFT transfers clear inside standard banking slots, Monday to Friday, excluding bank
holidays. RTGS is available for high-value settlements during RBI window hours.
If a settlement fails, the funds are automatically returned to the merchant wallet balance and
the payout is marked FAILED with the bank response code recorded against it.
Page 9: A payout stuck in PENDING beyond one settlement cycle should be checked with the payout
status API using its transaction ID before raising a ticket. A UTR is issued only once the bank
accepts the instruction, so a missing UTR means the instruction has not yet left DigiPay.
""",
    },
    {
        "source": "NPCI Chargeback Rules and Dispute SOP.pdf",
        "metadata": {"category": "dispute", "owner": "Compliance"},
        "content": """
# Chargeback and Dispute Window
Page 14: Chargeback complaints can be raised within 30 days from the transaction date.
Merchants must submit a valid UTR, RRN, the customer mobile number and the transaction receipt.
Settlement disputes must include a bank statement extract showing the non-credit.
Page 15: NPCI adjustment cycles run T+1 for AePS and T+2 for UPI. A chargeback raised after the
30-day window is rejected at the network and cannot be re-opened by DigiPay support.
Deemed-accepted chargebacks are debited from the merchant wallet automatically.
""",
    },
    {
        "source": "Aadhaar Face RD Integration Guide.pdf",
        "metadata": {"category": "device", "owner": "Engineering"},
        "content": """
# Biometric RD Service Installation
Page 3: CSC VLEs must install the official UIDAI Face RD application (version 2.1 or later) from
the Google Play Store. Ensure the camera permission is granted and the device registration
status shows ACTIVE before attempting a biometric transaction.
Page 4: For USB fingerprint scanners, OTG must be enabled in Android settings and the
manufacturer RD service (Mantra, Morpho, Startek, Precision) must be installed and registered.
Clean the sensor surface and the camera lens. Keep the face inside the guide box with even
front lighting and no backlight.
Page 5: A device that shows NOT_REGISTERED must be registered from the DigiPay app. Device
registration cannot be performed through support chat.
""",
    },
    {
        "source": "AePS Transaction Limits and Conduct SOP.pdf",
        "metadata": {"category": "limits", "owner": "Compliance"},
        "content": """
# AePS Limits and VLE Conduct
Page 2: The standard AePS single transaction limit is Rs 10,000. A customer is limited to
5 withdrawals per day across the network. Balance enquiry has no value limit but is rate limited.
Page 3: VLEs are strictly prohibited from split-charging, from demanding a processing fee from
customers, and from retaining any part of a withdrawal. Violations lead to service block.
Page 4: A transaction that times out at the switch is auto-reconciled in the next settlement
cycle. Timed-out AePS transactions appear in the admin timeout list and must not be retried
until reconciliation completes, to avoid a double debit to the customer.
""",
    },
    {
        "source": "KYC Approval SLA and Rejections SOP.pdf",
        "metadata": {"category": "kyc", "owner": "Onboarding"},
        "content": """
# KYC Approval SLA
Page 1: KYC reviews complete within 24 to 48 business hours of document upload. PAN and Aadhaar
copies must be scanned flat, in colour, and fully legible. The name must match the bank account
exactly. Address proof must correspond to the active merchant business site.
Page 2: The most common rejection reasons are a name mismatch against the bank account, a
cropped or glare-affected document image, and an address proof older than three months.
A rejected KYC can be re-submitted immediately with corrected documents.
""",
    },
    {
        "source": "DigiPay Transaction Status Interpretation Guide.pdf",
        "metadata": {"category": "transaction", "owner": "Support"},
        "content": """
# Reading a DigiPay Transaction Status
Page 1: SUCCESS means the switch confirmed the transaction and the ledger has been posted.
FAILED means the switch declined it and no ledger impact remains after reversal.
PENDING means DigiPay is awaiting the switch response; do not retry a pending transaction.
TIMEOUT means no response arrived within the switch window and reconciliation will resolve it.
Page 2: The RRN is the network reference and is the identifier a bank needs for a customer
dispute. The UTR identifies a settlement leg, not a customer transaction. The DigiPay txnId is
internal and is what support and this assistant use for a lookup.
Page 3: A customer-debited-but-not-paid case is resolved by the reconciliation cycle within
T+1 for AePS. Raise a ticket with the RRN if it remains unresolved after that.
""",
    },
]


def build_capability_document() -> Dict[str, Any]:
    """Capability document generated from the live tool registry."""
    from tools.catalog import catalog_markdown

    return {
        "source": "DigiPay Assistant Capabilities.md",
        "metadata": {"category": "capability", "generated": True},
        "content": catalog_markdown(),
    }


def build_boundary_document() -> Dict[str, Any]:
    """
    Read-only boundary document generated from the gateway allow-list and the
    exclusion register, so the assistant explains its own limits accurately.
    """
    from gateway.v2.safety import ALLOWED_ENDPOINTS, EXCLUDED_ENDPOINTS

    reason_guidance = {
        "MONEY_MOVEMENT": "Perform this in the DigiPay app, which enforces the biometric and OTP checks the transaction requires.",
        "WRITE": "Perform this in the DigiPay app or admin portal, where the change is attributed to a signed-in user.",
        "AUTH": "Authentication must happen in the DigiPay app so the customer's consent and biometrics are captured correctly.",
        "CALLBACK": "This is an inbound integration endpoint used by partner systems, not a user-facing action.",
        "UNSUPPORTED": "This endpoint needs a transport or payload format chat cannot provide.",
    }

    lines = [
        "# What the DigiPay Assistant Can and Cannot Do",
        "",
        "Page 1: The assistant has read-only access to the DigiPay gateway. It can retrieve and",
        "explain records. It cannot change anything. This is enforced in code by an endpoint",
        "allow-list, not by policy alone, so a request to act is refused rather than attempted.",
        "",
        "## Readable data",
    ]
    by_controller: Dict[str, List[str]] = {}
    for spec in ALLOWED_ENDPOINTS:
        by_controller.setdefault(spec.controller, []).append(spec.summary)
    for controller in sorted(by_controller):
        lines.append(f"- **{controller}**: " + "; ".join(sorted(set(by_controller[controller]))))

    lines += ["", "Page 2: ## Actions the assistant will not perform", ""]
    by_reason: Dict[str, List[str]] = {}
    for _, path, reason, note in EXCLUDED_ENDPOINTS:
        by_reason.setdefault(reason, []).append(note)
    for reason in sorted(by_reason):
        lines.append(f"### {reason.replace('_', ' ').title()}")
        for note in sorted(set(by_reason[reason])):
            lines.append(f"- {note}")
        lines.append(f"  - {reason_guidance.get(reason, 'Use the DigiPay app or portal instead.')}")
        lines.append("")

    return {
        "source": "DigiPay Assistant Boundaries.md",
        "metadata": {"category": "boundary", "generated": True},
        "content": "\n".join(lines),
    }


def all_seed_documents() -> List[Dict[str, Any]]:
    """
    The corpus indexed for retrieval: the SOP documents plus the boundary document.

    The capability document is deliberately NOT indexed. "What can you do?" is
    answered directly from the live tool registry by the response node, so
    retrieval is never needed for it — while indexing it actively hurt every other
    query: it is long, it names every domain (status, device, transaction,
    settlement), and its chunks outnumbered all the SOPs combined, so it crowded
    out the topic-specific documents on questions like "what does PENDING mean".
    `build_capability_document` is still used by the governance API and to export
    the capability sheet.
    """
    return SOP_DOCUMENTS + [build_boundary_document()]
