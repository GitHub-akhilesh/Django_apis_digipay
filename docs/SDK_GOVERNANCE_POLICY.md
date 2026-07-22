# DigiPay SDK Governance & Compatibility Policy

> **Architecture Review Board (ARB) Status**: Approved (Overall Score: **9.8–9.9/10**).
> The platform transition from **Build Phase** to **Product Phase** is complete. Architecture is frozen at **v2.0.0-beta**.

---

## 🏆 ARB Assessment & Scorecard

| Area | Status | Notes |
| :--- | :--- | :--- |
| **AI Platform Orchestration** | ✅ Production-ready | FastAPI + LangGraph Agent |
| **Core SDK Architecture** | ✅ Excellent | `@digipay/chat-core` Monorepo Package |
| **React Component Library** | ✅ Excellent | `@digipay/chat-react` Context & Hooks |
| **Web Components Platform** | ✅ Excellent | `<digipay-chat mode="...">` Custom Element |
| **Developer Experience (DX)** | ✅ Strong | 1-line HTML & React integration |
| **API Governance** | ✅ Strong | Contracts locked & frozen at v2.0.0-beta |
| **Packaging & CI/CD** | 🟡 Active Phase E | NPM Workspaces & ESM/CommonJS distribution |
| **Production Rollout** | 🟡 Active Phase H | Staged rollout (Internal -> Sandbox -> Merchant -> Admin) |

---

## ⚖️ SDK Governance & Versioning Rules

DigiPay SDKs follow **Semantic Versioning (SemVer 2.0.0)**: `MAJOR.MINOR.PATCH`

### 1. Versioning Commitments
- **PATCH (`x.x.N`)**: Backwards-compatible bug fixes and security patches. No public API contract changes.
- **MINOR (`x.N.0`)**: Backwards-compatible new features, new plugins, or optional configuration props.
- **MAJOR (`N.0.0`)**: Breaking contract changes. Requires minimum **6 months deprecation notice** and migration guides.

### 2. Supported Compatibility Matrix

| Dependency / Environment | Supported Versions |
| :--- | :--- |
| **Browsers** | Chrome 90+, Edge 90+, Firefox 88+, Safari 14+ |
| **Node.js** | `>= 16.0.0` |
| **React / React DOM** | `>= 16.8.0` (Hooks compliant) |
| **TypeScript** | `>= 4.5.0` |

---

## 📊 Engineering Resource Allocation Ratios

From this milestone forward, engineering effort across the platform is allocated as follows:

```
┌────────────────────────────────────────────────────────────────────────┐
│ 40% Developer Experience (Docs, Storybook, Tooling, Examples)         │
├────────────────────────────────────────────────────────────────────────┤
│ 30% Production Rollout & Operational Monitoring                        │
├────────────────────────────────────────────────────────────────────────┤
│ 20% Quality Engineering (Playwright E2E, Accessibility, CI/CD)         │
├────────────────────────────────────────────────────────────────────────┤
│ 10% Feature Enhancements (Driven by User Feedback)                    │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Staged Production Rollout Strategy (Phase H)

```
┌─────────────────────────┐     ┌─────────────────────────┐     ┌─────────────────────────┐
│ STAGE 1: Internal       │ ──> │ STAGE 2: Merchant       │ ──> │ STAGE 3: Full Enterprise│
│ Sandbox & Dev Teams     │     │ Portal (5 -> 100 users) │     │ Admin & Operations      │
└─────────────────────────┘     └─────────────────────────┘     └─────────────────────────┘
```

---

## 📁 Related Governance Documents

- **v2.0.0-beta Release Manifest**: [RELEASE_MANIFEST_v2.0.0-beta.md](file:///d:/Office-Projects/Django_apis_digipay/docs/RELEASE_MANIFEST_v2.0.0-beta.md)
- **Developer DX Portal**: [DEVELOPER_PORTAL.md](file:///d:/Office-Projects/Django_apis_digipay/docs/DEVELOPER_PORTAL.md)
- **Walkthrough**: [walkthrough.md](file:///C:/Users/CSCSPV2084/.gemini/antigravity-ide/brain/2b291c97-1176-4450-b282-fcee6fef90bc/walkthrough.md)
