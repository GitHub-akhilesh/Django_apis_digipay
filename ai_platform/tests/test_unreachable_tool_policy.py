"""
Tools whose backing endpoints the configured gateway does not serve must not be
offered to the model.

Eleven pre-existing tools call settings.SERVICE_ENDPOINTS prefixes (/wallet,
/merchant, /transaction, /ledger, /passbook, /aeps, /notification, /ticket) on
API_GATEWAY_URL. The DigiPay Spring gateway serves /v2/* and /v1/upi/* only, so
each of those calls returns 401 and the assistant answers "I have flagged this
for Level-2 human support" — indistinguishable, to a user, from the platform
being broken.

Nothing is deleted: they stay registered and callable, and
LEGACY_MICROSERVICE_ENDPOINTS_ENABLED=true restores them for a backend that does
serve those prefixes. Until then they are marked UNREACHABLE and withheld from
the catalogue so the planner picks a gateway tool that works.
"""

import pytest

from core.config import settings
from tools.catalog import build_tool_catalog, visible_tools
from tools.registry import (
    HEALTH_UNREACHABLE,
    LEGACY_MICROSERVICE_TOOLS,
    LEGACY_TOOL_REPLACEMENTS,
    TOOL_REGISTRY,
)


def test_legacy_microservice_tools_are_still_registered():
    """"Keep the old APIs intact" - they are marked, never removed."""
    for name in LEGACY_MICROSERVICE_TOOLS:
        assert name in TOOL_REGISTRY, f"{name} must remain registered"


@pytest.mark.skipif(
    settings.LEGACY_MICROSERVICE_ENDPOINTS_ENABLED,
    reason="deployment declares the SERVICE_ENDPOINTS prefixes are served",
)
def test_unreachable_tools_are_marked():
    for name in LEGACY_MICROSERVICE_TOOLS:
        assert TOOL_REGISTRY[name].health == HEALTH_UNREACHABLE, (
            f"{name} targets a prefix the gateway does not serve and must be "
            "marked UNREACHABLE"
        )


@pytest.mark.skipif(
    settings.LEGACY_MICROSERVICE_ENDPOINTS_ENABLED,
    reason="deployment declares the SERVICE_ENDPOINTS prefixes are served",
)
def test_unreachable_tools_are_hidden_from_the_model():
    """
    The catalogue is what the planner chooses from. Listing a tool that always
    401s guarantees the escalation message instead of an answer.
    """
    offered = {meta.name for meta in visible_tools()}
    leaked = sorted(LEGACY_MICROSERVICE_TOOLS & offered)
    assert leaked == [], f"unreachable tools offered to the model: {leaked}"

    catalog = build_tool_catalog()
    for name in LEGACY_MICROSERVICE_TOOLS:
        assert name not in catalog, f"{name} appears in the prompt catalogue"


def test_a_working_replacement_is_offered_for_each_hidden_read_tool():
    """
    Hiding a tool must not remove a capability outright: every read-only tool
    withheld here needs a live gateway equivalent, or users lose the feature.
    """
    offered = {meta.name for meta in visible_tools()}
    missing = []
    for name in sorted(LEGACY_MICROSERVICE_TOOLS):
        meta = TOOL_REGISTRY[name]
        if not meta.read_only:
            continue  # write tools are deliberately not replaced
        replacement = LEGACY_TOOL_REPLACEMENTS.get(name)
        if replacement is None:
            continue  # explicitly acknowledged as having no equivalent
        if replacement not in offered:
            missing.append(f"{name} -> {replacement}")
    assert missing == [], f"replacement tools not available: {missing}"


def test_replacement_map_covers_every_hidden_tool():
    """A tool hidden without a documented decision is an accident."""
    undocumented = sorted(LEGACY_MICROSERVICE_TOOLS - set(LEGACY_TOOL_REPLACEMENTS))
    assert undocumented == [], (
        f"add these to LEGACY_TOOL_REPLACEMENTS (use None if no equivalent): {undocumented}"
    )


def test_gateway_tools_remain_healthy():
    """The marking must not catch tools backed by live /v2 endpoints."""
    from tools.decorator import SOURCE_GATEWAY_V2

    for meta in TOOL_REGISTRY.values():
        if meta.source == SOURCE_GATEWAY_V2:
            assert meta.health == "HEALTHY", f"{meta.name} was wrongly marked {meta.health}"


def test_unreachable_tools_can_be_inspected_deliberately():
    """Diagnostics still need to see them; only the model's view is filtered."""
    all_tools = {meta.name for meta in visible_tools(include_unreachable=True)}
    assert LEGACY_MICROSERVICE_TOOLS <= all_tools


def test_balance_question_selects_the_reachable_tool():
    """End of the chain: the user's question reaches a tool that can answer it."""
    offered = {meta.name for meta in visible_tools()}
    assert "getLedgerBalanceV2" in offered
    assert "getWalletBalance" not in offered
