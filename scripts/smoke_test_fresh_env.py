"""
DigiPay Developer Platform - Fresh Environment Cold-Start Smoke Test Script
Simulates a cold-start developer onboarding flow: verifies repo files, bundle budgets, API contracts, local validation, and full-stack runner.
"""

import sys
import os
import subprocess

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

def print_banner(step_num, title):
    print(f"\n==================================================")
    print(f" STEP {step_num}: {title}")
    print("==================================================")

def run_python_script(script_relative_path):
    script_path = os.path.join(repo_root, script_relative_path)
    res = subprocess.run([sys.executable, script_path], cwd=repo_root, capture_output=True, text=True)
    if res.returncode == 0:
        print(f"  [PASS] {script_relative_path} succeeded.")
        return True
    else:
        print(f"  [FAIL] {script_relative_path} failed:\n{res.stderr or res.stdout}")
        return False

def main():
    print("==================================================")
    print("DigiPay SDK - Fresh Environment Cold-Start Smoke Test")
    print("==================================================")

    steps = [
        ("Bundle Budget Check", "scripts/check_bundle_budget.py"),
        ("API Contract Tests", "tests/contract/test_sdk_api_contracts.py"),
        ("Security Guardrails", "tests/security/test_security_guardrails.py"),
        ("Local Phase 1 Validation", "scripts/validate_local.py"),
        ("Full-Stack Orchestration", "scripts/run_full_stack.py")
    ]

    all_passed = True
    for idx, (title, script) in enumerate(steps, 1):
        print_banner(idx, title)
        passed = run_python_script(script)
        if not passed:
            all_passed = False

    print("\n--------------------------------------------------")
    if all_passed:
        print("[SUCCESS] FRESH ENVIRONMENT SMOKE TEST PASSED 100%!")
        sys.exit(0)
    else:
        print("[FAIL] Fresh environment smoke test encountered failures.")
        sys.exit(1)

if __name__ == "__main__":
    main()
