"""
Tracing module compatibility facade re-exporting context variables and middleware handlers from monitoring.mdc.
"""

from monitoring.mdc import (
    correlation_id_var,
    trace_id_var,
    span_id_var,
    parent_span_id_var,
    request_id_var,
    session_id_var,
    txn_id_var,
    merchant_id_var,
    user_id_var,
    service_name_var,
    channel_var,
    tenant_id_var,
    operation_var,
    client_ip_var,
    endpoint_var,
    latency_var,
    status_code_var,
    TraceContext,
    get_correlation_id,
    get_trace_id,
    get_current_trace_id,
    get_span_id,
    get_current_span_id,
    get_request_id,
    get_txn_id
)
from monitoring.middleware import TracingMiddleware

__all__ = [
    "correlation_id_var",
    "trace_id_var",
    "span_id_var",
    "parent_span_id_var",
    "request_id_var",
    "session_id_var",
    "txn_id_var",
    "merchant_id_var",
    "user_id_var",
    "service_name_var",
    "channel_var",
    "tenant_id_var",
    "operation_var",
    "client_ip_var",
    "endpoint_var",
    "latency_var",
    "status_code_var",
    "TraceContext",
    "TracingMiddleware",
    "get_correlation_id",
    "get_trace_id",
    "get_current_trace_id",
    "get_span_id",
    "get_current_span_id",
    "get_request_id",
    "get_txn_id"
]
