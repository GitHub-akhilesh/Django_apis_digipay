# Release Manifest — v2.0.0-RC1

**Release Date:** 2026-07-22  
**Release Type:** Candidate Release (Internal Merchant & Admin Portals)  
**Architecture Status:** [FROZEN] Complete  

---

## Bundle Size Report

| Asset | Size | Status | Target Limit |
|---|---|---|---|
| `digipay-chat-sdk.js` | **4.63 KB** | [PASS] Compliant | < 15 KB |
| `digipay-chat-widget.js` | **10.45 KB** | [PASS] Compliant | < 30 KB |

---

## Changelog (v2.0.0-beta -> v2.0.0-RC1)

- **Testing & E2E Validation**: Completed Phase 1 (Local Validation), Phase 2 (Multi-browser Chrome/Edge/Firefox/Safari), and Phase 3 (Journeys 1-5).
- **Performance & Load**: Verified 10, 50, 100, 500 concurrent sessions with p95 latency < 150ms.
- **Accessibility & Security**: Integrated WCAG 2.1 AA keyboard nav and security guardrails for PII and Prompt Injection.
- **Storybook**: Added Storybook stories for `@digipay/chat-react`.
- **Telemetry**: Implemented SDK Telemetry Dashboard tracking widget open rates and session metrics.
- **NPM Publishing**: Configured `.npmrc` and GitHub Actions publishing workflow for `@digipay/chat-core` and `@digipay/chat-react`.

---

## API Contract Diff

```diff
  // @digipay/chat-react v2.0.0-RC1 Contract
+ export interface DigiPayChatWidgetProps {
+   cscId: string;
+   mode?: 'floating' | 'sidebar' | 'inline';
+   theme?: 'light' | 'dark' | 'system';
+   primaryColor?: string;
+ }
```

---

## Test Matrix Summary

- **Pytest Unit & Security Guardrails**: 100% Passed (6/6)
- **Playwright Multi-Browser E2E**: 100% Passed (Chrome, Edge, Firefox, WebKit, Mobile)
- **Local Health & Stream Handshake**: 100% Passed

---

## Compatibility Matrix

- **Browser Support**: Chrome >= 90, Edge >= 90, Firefox >= 88, Safari >= 14, iOS Safari >= 14, Android Chrome >= 90
- **React Support**: React 17.x, React 18.x
- **Node.js Support**: Node 18.x, Node 20.x
