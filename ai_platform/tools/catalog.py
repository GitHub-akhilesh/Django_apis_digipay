"""
Tool catalogue generation.

The intent classifier and the DAG planner used to carry hard-coded lists of the
thirteen original tools inside their prompts. With the gateway-service
integration the registry is several times that size, and a hand-maintained list
would silently hide new tools from the model. Everything here is derived from
`TOOL_REGISTRY` instead, so the catalogue can never drift from what is
executable.

Catalogue text is deliberately formatted WITHOUT `argName:` or `argName=`
sequences: the offline LLM simulator in `llm.provider` scrapes the prompt for
`cscId:` / `txnId:` style patterns to derive its canned answers, and a colon
after an argument name in the catalogue would shadow the real caller context.
"""

import logging
from typing import Dict, List, Optional

from tools.decorator import ToolMetadata
from tools.registry import HEALTH_UNREACHABLE, TOOL_REGISTRY

logger = logging.getLogger("ai_platform.tools.catalog")


def visible_tools(
    roles: Optional[List[str]] = None,
    include_write: bool = True,
    include_deprecated: bool = False,
    include_unreachable: bool = False,
) -> List[ToolMetadata]:
    """
    Tools the caller is allowed to see, sorted by domain then name.

    Filtering by role at catalogue time keeps a merchant from being told about
    admin reports it would only be refused for — the RBAC check in
    `permission_service` remains the actual enforcement point.

    Tools marked UNREACHABLE are withheld too. Offering the model a tool whose
    backend does not serve its path guarantees a 401 and an escalation message,
    which looks to the user like the platform is broken; withholding it makes the
    planner choose a working alternative instead. See
    `tools.registry.LEGACY_MICROSERVICE_TOOLS`.
    """
    tools: List[ToolMetadata] = []
    for meta in TOOL_REGISTRY.values():
        if meta.deprecated and not include_deprecated:
            continue
        if meta.health == HEALTH_UNREACHABLE and not include_unreachable:
            continue
        if not include_write and not meta.read_only:
            continue
        if roles and not any(role in meta.roles for role in roles):
            continue
        tools.append(meta)

    return sorted(tools, key=lambda m: (m.domain, m.name))


def build_tool_catalog(
    roles: Optional[List[str]] = None,
    include_write: bool = True,
    include_examples: bool = False,
) -> str:
    """Render the catalogue as prompt text grouped by domain."""
    tools = visible_tools(roles=roles, include_write=include_write)
    if not tools:
        return "(no tools available for this caller)"

    grouped: Dict[str, List[ToolMetadata]] = {}
    for meta in tools:
        grouped.setdefault(meta.domain, []).append(meta)

    lines: List[str] = []
    for domain in sorted(grouped):
        lines.append(f"[{domain}]")
        for meta in grouped[domain]:
            lines.append(f"- {meta.name} — {meta.description}")
            if meta.required_args:
                lines.append(f"    required args → {', '.join(meta.required_args)}")
            if meta.optional_args:
                lines.append(f"    optional args → {', '.join(meta.optional_args)}")
            if not meta.read_only:
                lines.append("    NOTE → this tool changes state and needs explicit user confirmation")
            if include_examples and meta.examples:
                lines.append(f"    asked as → {'; '.join(meta.examples[:3])}")
        lines.append("")

    return "\n".join(lines).strip()


def tool_names(roles: Optional[List[str]] = None, include_write: bool = True) -> List[str]:
    return [m.name for m in visible_tools(roles=roles, include_write=include_write)]


def read_only_tool_names() -> List[str]:
    """Names of every tool whose backing API only reads — used for cache eligibility."""
    return [m.name for m in TOOL_REGISTRY.values() if m.read_only]


def catalog_summary() -> Dict[str, object]:
    """Counts by domain and source, for the governance API and health checks."""
    by_domain: Dict[str, int] = {}
    by_source: Dict[str, int] = {}
    read_only = 0
    for meta in TOOL_REGISTRY.values():
        by_domain[meta.domain] = by_domain.get(meta.domain, 0) + 1
        by_source[meta.source] = by_source.get(meta.source, 0) + 1
        if meta.read_only:
            read_only += 1
    return {
        "totalTools": len(TOOL_REGISTRY),
        "readOnlyTools": read_only,
        "stateChangingTools": len(TOOL_REGISTRY) - read_only,
        "byDomain": dict(sorted(by_domain.items())),
        "bySource": dict(sorted(by_source.items())),
    }


def catalog_markdown() -> str:
    """
    Human-readable capability document.

    Indexed into the MongoDB RAG store so questions like "what can you do?" or
    "can you check my device registration?" are answered from the live registry
    rather than from a stale hand-written FAQ.
    """
    tools = visible_tools()
    grouped: Dict[str, List[ToolMetadata]] = {}
    for meta in tools:
        grouped.setdefault(meta.domain, []).append(meta)

    lines = [
        "# DigiPay Assistant Capabilities",
        "",
        "Page 1: These are the DigiPay operations the assistant can perform on request.",
        "The assistant reads data only. It cannot start, reverse or settle a transaction,",
        "register or remove a device, create or delete records, authenticate a customer,",
        "or send an OTP — those actions must be done in the DigiPay app or portal.",
        "",
    ]
    for domain in sorted(grouped):
        lines.append(f"## {domain.title()}")
        for meta in grouped[domain]:
            lines.append(f"- **{meta.name}** — {meta.description}")
            if meta.endpoint:
                lines.append(f"  - Backed by `{meta.endpoint}`")
            if meta.roles and len(meta.roles) < 4:
                lines.append(f"  - Available to: {', '.join(meta.roles)}")
            if meta.examples:
                lines.append(f"  - Ask it like: {'; '.join(meta.examples[:3])}")
        lines.append("")

    return "\n".join(lines)
