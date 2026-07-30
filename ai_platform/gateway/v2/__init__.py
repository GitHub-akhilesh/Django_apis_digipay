"""
Read-only SDK for the DigiPay Spring Boot gateway-service.

This package is additive: `gateway.base_client` / `gateway.client` and the
existing legacy DigiPay clients are untouched and keep serving the tools that
already depend on them.
"""

from gateway.v2.admin_client import admin_v2_client
from gateway.v2.aeps_client import aeps_v2_client
from gateway.v2.ledger_client import ledger_v2_client
from gateway.v2.notification_client import notification_v2_client
from gateway.v2.platform_client import (
    analytics_v2_client,
    device_v2_client,
    external_partner_v2_client,
    operator_v2_client,
    service_catalog_v2_client,
    status_v2_client,
    upi_v2_client,
    user_v2_client,
)
from gateway.v2.txn_client import txn_log_v2_client

__all__ = [
    "admin_v2_client",
    "aeps_v2_client",
    "analytics_v2_client",
    "device_v2_client",
    "external_partner_v2_client",
    "ledger_v2_client",
    "notification_v2_client",
    "operator_v2_client",
    "service_catalog_v2_client",
    "status_v2_client",
    "txn_log_v2_client",
    "upi_v2_client",
    "user_v2_client",
]
