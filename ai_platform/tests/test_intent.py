import pytest
from intent.classifier import IntentClassifier

@pytest.mark.anyio
async def test_intent_classification():
    res = await IntentClassifier.classify(
        message="What is my wallet balance?",
        csc_id="500100100014"
    )
    assert res["intent"] == "Wallet"
    assert len(res["tool_calls"]) > 0
    assert res["tool_calls"][0]["name"] == "getWalletBalance"
