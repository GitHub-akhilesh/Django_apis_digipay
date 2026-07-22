from typing import List, Dict, Any

BENCHMARK_DATASET: List[Dict[str, Any]] = [
    {
        "question": "What is my merchant wallet balance?",
        "expected_intent": "Wallet",
        "expected_tools": ["getWalletBalance"],
        "expected_params": ["merchantId"],
        "answer_pattern": "balance"
    },
    {
        "question": "Show daily limits for my wallet",
        "expected_intent": "Wallet",
        "expected_tools": ["getLimits"],
        "expected_params": ["merchantId"],
        "answer_pattern": "limit"
    },
    {
        "question": "Please reverse transaction 123",
        "expected_intent": "Transaction",
        "expected_tools": ["reverseTransaction"],
        "expected_params": ["txnId"],
        "answer_pattern": "reversal"
    },
    {
        "question": "How do I settle my stuck payouts?",
        "expected_intent": "FAQ",
        "expected_tools": [],
        "expected_params": [],
        "answer_pattern": "settlement"
    }
]
