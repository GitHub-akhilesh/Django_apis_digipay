import pytest
from evaluation.datasets import BENCHMARK_DATASET
from evaluation.scoring import evaluation_scorer
from evaluation.hallucination import hallucination_detector
from evaluation.regression import regression_guard
from evaluation.benchmark import benchmark_runner
from agent.orchestrator import AgentOrchestrator

def test_benchmark_dataset_elements():
    assert len(BENCHMARK_DATASET) == 4
    assert BENCHMARK_DATASET[0]["expected_intent"] == "Wallet"

def test_evaluation_scoring():
    run_results = [
        {"intent": "Wallet", "selected_tools": ["getWalletBalance"], "parameters": {"merchantId": "500100100014"}, "response": "balance is ₹4500"},
        {"intent": "Wallet", "selected_tools": ["getLimits"], "parameters": {"merchantId": "500100100014"}, "response": "limit set"},
        {"intent": "Transaction", "selected_tools": ["reverseTransaction"], "parameters": {"txnId": "123"}, "response": "reversal complete"},
        {"intent": "FAQ", "selected_tools": [], "parameters": {}, "response": "settlement cycles"}
    ]
    scores = evaluation_scorer.calculate_scores(run_results, BENCHMARK_DATASET)
    assert scores["overallScorePct"] == 100.0
    assert scores["intentAccuracyPct"] == 100.0

def test_hallucination_detection():
    run_results = [
        {"response": "Your balance is ₹4560.50."}, # Grounded
        {"response": "Your balance is ₹9999.00."}  # Hallucinated
    ]
    rate = hallucination_detector.calculate_hallucination_rate(run_results)
    assert rate == 50.0

def test_regression_guard_thresholds():
    passing_scores = {
        "overallScorePct": 95.0,
        "intentAccuracyPct": 98.0,
        "toolAccuracyPct": 90.0
    }
    assert regression_guard.verify_regression(passing_scores) is True

    failing_scores = {
        "overallScorePct": 75.0,
        "intentAccuracyPct": 98.0,
        "toolAccuracyPct": 90.0
    }
    assert regression_guard.verify_regression(failing_scores) is False

@pytest.mark.anyio
async def test_benchmark_runner_pipeline(monkeypatch):
    async def mock_chat(session_id, message, csc_id, history, **kwargs):
        if "balance" in message.lower():
            return {
                "response": "Your balance is ₹4560.50",
                "intent": "Wallet",
                "escalate": False,
                "policy_checked": True,
                "explainability": {
                    "intent": "Wallet",
                    "selectedTools": ["getWalletBalance"],
                    "executionTimeMs": 15.0
                }
            }
        elif "limit" in message.lower():
            return {
                "response": "Your limit is 1000",
                "intent": "Wallet",
                "escalate": False,
                "policy_checked": True,
                "explainability": {
                    "intent": "Wallet",
                    "selectedTools": ["getLimits"],
                    "executionTimeMs": 12.0
                }
            }
        elif "reverse" in message.lower():
            return {
                "response": "Reversal processed successfully",
                "intent": "Transaction",
                "escalate": False,
                "policy_checked": True,
                "explainability": {
                    "intent": "Transaction",
                    "selectedTools": ["reverseTransaction"],
                    "executionTimeMs": 25.0
                }
            }
        else:
            return {
                "response": "Settlement FAQ info",
                "intent": "FAQ",
                "escalate": False,
                "policy_checked": True,
                "explainability": {
                    "intent": "FAQ",
                    "selectedTools": [],
                    "executionTimeMs": 8.0
                }
            }

    monkeypatch.setattr(AgentOrchestrator, "chat", mock_chat)

    res = await benchmark_runner.run_benchmark()
    assert res["success"] is True
    assert res["scores"]["overallScorePct"] == 100.0
