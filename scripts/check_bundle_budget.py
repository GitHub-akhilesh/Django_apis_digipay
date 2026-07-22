"""
DigiPay SDK - Bundle Size Budget & Regression Verification Enforcer
Enforces strict bundle budgets (digipay-chat-sdk.js <= 15 KB, digipay-chat-widget.js <= 30 KB). Fails CI if exceeded.
"""

import os
import sys

BUDGET_LIMITS_KB = {
    "digipay-chat-sdk.js": 15.0,     # Max 15 KB limit
    "digipay-chat-widget.js": 30.0   # Max 30 KB limit
}

def check_budgets():
    print("==================================================")
    print("DigiPay SDK - Bundle Size Budget Enforcer")
    print("==================================================")

    sdk_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sdk"))
    all_passed = True

    for filename, limit_kb in BUDGET_LIMITS_KB.items():
        filepath = os.path.join(sdk_dir, filename)
        if not os.path.exists(filepath):
            print(f"  [FAIL] Bundle file missing: {filename}")
            all_passed = False
            continue

        size_bytes = os.path.getsize(filepath)
        size_kb = round(size_bytes / 1024, 2)

        if size_kb <= limit_kb:
            print(f"  [PASS] {filename}: {size_kb} KB (Budget Limit: {limit_kb} KB)")
        else:
            print(f"  [FAIL] {filename}: {size_kb} KB EXCEEDS BUDGET LIMIT ({limit_kb} KB)!")
            all_passed = False

    print("--------------------------------------------------")
    if all_passed:
        print("[SUCCESS] All bundle sizes are within budget limits!")
        sys.exit(0)
    else:
        print("[ERROR] Bundle size regression detected! Aborting release.")
        sys.exit(1)

if __name__ == "__main__":
    check_budgets()
