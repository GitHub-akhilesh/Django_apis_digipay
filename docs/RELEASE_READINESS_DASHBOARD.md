# DigiPay Developer Platform — Live Release Readiness Dashboard

**Current Release Tag:** `v2.0.0-RC1`  
**Target Release:** `v2.0.0-GA`  
**Architecture Board Sign-off:** ✅ Approved for RC1  
**Last Updated:** 2026-07-22  

---

## 📊 Quality & Release Gate Summary

| Category | Component / Indicator | Target | Status | Sign-off Owner |
|---|---|---|---|---|
| **Architecture** | Core Engine & Schema Freeze | 100% Frozen | ✅ Complete | ARB Board |
| **Contract Testing** | `test_sdk_api_contracts.py` | 100% Passing | ✅ Complete | QA Team |
| **Unit Testing** | `pytest --cov=app --cov=ai_platform` | $\ge 90\%$ Coverage | ✅ Complete | Eng Team |
| **E2E Journeys** | Playwright (Chrome, Edge, Firefox, Safari, Mobile) | 100% Passing | ✅ Complete | QA Team |
| **Accessibility (a11y)** | WCAG 2.1 AA Keyboard & Screen Reader | 100% Compliant | ✅ Complete | UX Team |
| **Security Guardrails** | Prompt Injection, PII, JWT, Rate Limiting | 100% Passing | ✅ Complete | Security Team |
| **Performance KPIs** | Latency p95 $< 205\text{ms}$, SDK Init $< 40\text{ms}$ | Met Targets | ✅ Complete | Perf Team |
| **Bundle Budgets** | SDK $\le 15\text{KB}$, Widget $\le 30\text{KB}$ | 4.63KB & 10.45KB | ✅ Complete | Release Eng |
| **Documentation** | DevPortal, ADRs (0001-0007), Runbooks (01-07) | 100% Documented | ✅ Complete | Tech Writing |
| **Merchant Portal** | DigiPay React Merchant App Embed | Integrated | 🔄 RC1 Validation | Merchant Product Team |
| **Admin Portal** | DigiPay Support Admin App Embed | Integrated | 🔄 RC1 Validation | Admin Product Team |
| **Telemetry Health** | Live Metrics Dashboard (`telemetry.html`) | Active Stream | 🔄 Observing | DevOps Team |
| **GA Release Gate** | 2–4 Weeks Internal Bake Period | 0 Critical Bugs | ⏳ Pending RC1 | Platform Lead |

---

## 🚀 RC1 Exit Criteria Tracking

- [x] Full-stack orchestration runner (`python scripts/run_full_stack.py`) verified healthy.
- [x] Bundle size budgets enforced in CI (`scripts/check_bundle_budget.py`).
- [x] API contracts locked and verified (`tests/contract/test_sdk_api_contracts.py`).
- [x] Security guardrails verified (`tests/security/test_security_guardrails.py`).
- [x] Architecture Decision Records published (`docs/adr/`).
- [x] Operations Manual published (`docs/operations/`).
- [ ] 2-week internal production observation bake complete.
- [ ] GA Release Sign-off.
