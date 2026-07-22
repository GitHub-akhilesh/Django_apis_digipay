# Operations Runbook 03 — Telemetry & Monitoring

## Overview
Monitoring operational KPIs, telemetry dashboards, and alerting rules for the DigiPay AI Chat Platform.

## Core Operational KPIs
| Metric | Healthy Threshold | Critical Threshold |
|---|---|---|
| **Widget Open Rate** | $> 80\%$ | $< 50\%$ |
| **SDK Initialization Time** | $< 100\text{ms}$ | $> 500\text{ms}$ |
| **First Message Latency** | $< 1000\text{ms}$ | $> 3000\text{ms}$ |
| **Failed Initializations** | $< 0.05\%$ | $> 0.1\%$ |
| **WebSocket Reconnect Success** | $> 99\%$ | $< 95\%$ |

## Dashboard Location
- Live Developer Telemetry View: `docs/site/telemetry.html`
- Telemetry API Endpoint: `/api/v1/monitoring/telemetry`
