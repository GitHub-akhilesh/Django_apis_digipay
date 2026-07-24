import pytest
from app.schemas.enums import ToolName, TxnStatus
from app.services.intent_classifier import IntentClassifier
from app.services.response_builders import ResponseBuilderRegistry
from app.services.agent_service import AgentOrchestrator

def test_intent_classifier():
    res = IntentClassifier.classify_intent("Check my wallet balance", "500100100014")
    assert res["intent"] == "Wallet"
    assert len(res["tool_calls"]) == 1
    assert res["tool_calls"][0]["name"] == ToolName.GET_WALLET_BALANCE.value

def test_intent_classifier_old_balance():
    res = IntentClassifier.classify_intent("Check my old digipay balance", "500100100014")
    assert res["intent"] == "Wallet"
    assert res["tool_calls"][0]["name"] == ToolName.GET_OLD_DIGIPAY_BALANCE.value

    res2 = IntentClassifier.classify_intent("what is my old balance and legacy system wallet balance", "500100100014")
    assert res2["intent"] == "Wallet"
    assert res2["tool_calls"][0]["name"] == ToolName.GET_OLD_DIGIPAY_BALANCE.value

def test_intent_classifier_wallet_balance_locked():
    res = IntentClassifier.classify_intent("what is my wallet balance", "500100100014")
    assert res["intent"] == "Wallet"
    assert res["tool_calls"][0]["name"] == ToolName.GET_WALLET_BALANCE.value

def test_intent_classifier_settlement_and_txn_logs():
    res_prompt = IntentClassifier.classify_intent("Check my last settlement", "500100100014")
    assert res_prompt["intent"] == "Settlement"
    assert "From Date and To Date" in res_prompt["clarification_prompt"]

    res_settle = IntentClassifier.classify_intent("Check my settlement from 2026-06-01 to 2026-06-30", "500100100014")
    assert res_settle["intent"] == "Settlement"
    assert res_settle["confidence_score"] == 0.95
    assert res_settle["tool_calls"][0]["name"] == ToolName.GET_WALLET_BALANCE.value
    assert res_settle["tool_calls"][0]["args"]["fromDate"] == "2026-06-01"

    res_txns = IntentClassifier.classify_intent("what are my last txn of old system and related to it", "500100100014")
    assert res_txns["intent"] == "Wallet"
    assert res_txns["tool_calls"][0]["name"] == ToolName.GET_TXN_LOGS.value
    assert res_txns["tool_calls"][0]["args"]["rpp"] == 10

def test_intent_classifier_date_range_parsing():
    res_iso = IntentClassifier.classify_intent("transaction logs from 2026-06-01 to 2026-06-15", "500100100014")
    args_iso = res_iso["tool_calls"][0]["args"]
    assert args_iso["fromDate"] == "2026-06-01"
    assert args_iso["toDate"] == "2026-06-15"

    res_rel = IntentClassifier.classify_intent("transaction logs for last 7 days", "500100100014")
    args_rel = res_rel["tool_calls"][0]["args"]
    assert args_rel["fromDate"] != args_rel["toDate"]

def test_response_builder_registry():
    wallet_res = {
        "merchantId": "500100100014",
        "balance": 1500.50,
        "oldDigipayBalance": 1500.50,
        "blockedBalance": 0.0,
        "lastSettlementDate": "2026-06-01 10:00:00",
        "lastSettlementAmount": 500.0
    }
    formatted = ResponseBuilderRegistry.format_response(ToolName.GET_WALLET_BALANCE.value, wallet_res)
    assert "₹1500.50" in formatted
    assert "Old DigiPay balance is ₹1500.50" in formatted

@pytest.mark.asyncio
async def test_agent_orchestrator(db_session):
    res = await AgentOrchestrator.chat(db_session, "sess_1", "Check my wallet balance", "500100100014", [])
    assert res["status"] == "OK"
    assert "balance" in res["response"].lower()
