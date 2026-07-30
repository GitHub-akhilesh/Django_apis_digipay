import pytest
from intent.classifier import IntentClassifier


@pytest.mark.anyio
async def test_intent_classification():
    """
    A balance question must route to the gateway's ledger balance tool.

    This previously asserted intent "Wallet" and the pre-existing
    getWalletBalance tool. That tool calls /wallet/balance, a prefix the DigiPay
    Spring gateway does not serve, so against a real gateway it returns 401 and
    the user is told their request was "flagged for Level-2 human support"
    instead of being given a balance. getLedgerBalanceV2 (GET /v2/ledger/balance)
    is the endpoint that actually exists.
    """
    res = await IntentClassifier.classify(
        message="What is my wallet balance?",
        csc_id="500100100014"
    )
    assert res["intent"] == "LEDGER_BALANCE"
    assert len(res["tool_calls"]) > 0
    assert res["tool_calls"][0]["name"] == "getLedgerBalanceV2"
    # The caller's own CSC ID must be filled in, never invented.
    assert res["tool_calls"][0]["args"]["cscId"] == "500100100014"


@pytest.mark.anyio
async def test_balance_phrasings_all_reach_the_working_tool():
    """Users ask for a balance in several ways; none should hit a dead endpoint."""
    for message in (
        "Check my wallet balance",
        "what is my ledger balance",
        "how much balance do I have",
        "show my available balance",
    ):
        res = await IntentClassifier.classify(message=message, csc_id="500100100014")
        assert res["tool_calls"], f"no tool selected for {message!r}"
        assert res["tool_calls"][0]["name"] == "getLedgerBalanceV2", (
            f"{message!r} routed to {res['tool_calls'][0]['name']}"
        )
