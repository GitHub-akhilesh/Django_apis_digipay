# DigiPay Developer Platform — GA Program Roadmap & Master Plan

Master roadmap outlining the 6 core EPICS required to transition the platform from **RC1 Candidate Release to General Availability (GA)**.

---

## 🎯 Program Milestones & Status

| Phase | Milestone | Status | Target Completion |
|---|---|---|---|
| Phase 1 | Architecture & SDK Monorepo Freeze | ✅ Completed | v2.0.0-beta |
| Phase 2 | Release Engineering & CI/CD Pipelines | ✅ Completed | v2.0.0-RC1 |
| Phase 3 | Production Adoption & Telemetry Gate | 🟡 In Progress | RC1 $\rightarrow$ RC2 |
| Phase 4 | General Availability (GA) Sign-off | ⬜ Pending | v2.0.0-GA |

---

## 📌 Core Epics & Target Outcomes

### EPIC 1: Merchant Portal Production Adoption
- Embed `<digipay-chat>` widget into DigiPay Merchant Portal.
- Gather production usage telemetry, open rates, and merchant user feedback.

### EPIC 2: Admin Portal Production Adoption
- Embed Chat assistant into internal DigiPay Admin Portal for support agents.
- Verify multi-tenant token isolation and escalation handoff interfaces.

### EPIC 3: Storybook Publishing & Visual Regression Suite
- Host Storybook catalog for UI widget variants.
- Automate visual regression snapshot testing across Light/Dark themes and responsive modes.

### EPIC 4: Operational Telemetry & Monitoring Dashboards
- Surface live metrics: Widget Open Rate, Messages/Session, Escalation Rate, Failed Initializations, Version Distribution.
- Connect alerts to error thresholds ($> 0.1\%$ failure rate triggers PagerDuty).

### EPIC 5: SDK Scaffolder Tooling (`create-digipay-chat`)
- Publish `npx create-digipay-chat` scaffolding CLI for React, Vite, Next.js, and HTML templates.
- Maintain starter examples in `examples/`.

### EPIC 6: General Availability (GA) Release Gate
- Minimum 2–4 weeks of internal production bake time.
- 0 open critical defects.
- Formal sign-off from Platform Engineering & Architecture Review Board.

---

## 🚀 Progress Tracker Checklist

- [x] Architecture & Transports
- [x] SDK & Component Monorepo
- [x] Governance & Security Guardrails
- [x] Contract & Performance Testing
- [x] Release Engineering & Bundle Budgets
- [x] ADR Decision Records (0001-0007)
- [x] Scaffolder CLI (`create-digipay-chat`)
- [x] Visual Theme Builder
- [x] Plugin Marketplace Infrastructure
- [ ] Merchant Portal Production Rollout
- [ ] Admin Portal Production Rollout
- [ ] GA Readiness Sign-off
