import uuid
from typing import Dict, Optional
from contextvars import ContextVar
from core.constants import (
    HEADER_B3_TRACE_ID,
    HEADER_B3_SPAN_ID,
    HEADER_B3_PARENT_SPAN_ID,
    HEADER_B3_SAMPLED,
    HEADER_CORRELATION_ID,
    HEADER_REQUEST_ID,
    HEADER_TXN_ID
)

# Thread-safe ContextVars (Equivalent to Java SLF4J MDC)
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")
span_id_var: ContextVar[str] = ContextVar("span_id", default="")
parent_span_id_var: ContextVar[str] = ContextVar("parent_span_id", default="")
request_id_var: ContextVar[str] = ContextVar("request_id", default="")
session_id_var: ContextVar[str] = ContextVar("session_id", default="")
txn_id_var: ContextVar[str] = ContextVar("txn_id", default="")
merchant_id_var: ContextVar[str] = ContextVar("merchant_id", default="")
user_id_var: ContextVar[str] = ContextVar("user_id", default="")
client_ip_var: ContextVar[str] = ContextVar("client_ip", default="")
endpoint_var: ContextVar[str] = ContextVar("endpoint", default="")
latency_var: ContextVar[float] = ContextVar("latency", default=0.0)
status_code_var: ContextVar[int] = ContextVar("status_code", default=200)

class TraceContext:
    """
    Manages tracing contexts and produces B3 headers for downstream Spring calls.
    """
    @staticmethod
    def generate_trace_id() -> str:
        return uuid.uuid4().hex

    @staticmethod
    def generate_span_id() -> str:
        return uuid.uuid4().hex[:16]

    @staticmethod
    def generate_correlation_id() -> str:
        return f"corr-{uuid.uuid4().hex[:12]}"

    @staticmethod
    def generate_request_id() -> str:
        return f"req-{uuid.uuid4().hex[:12]}"

    @classmethod
    def get_b3_headers(cls) -> Dict[str, str]:
        """
        Constructs outgoing B3 propagation headers for HTTP clients (GatewayClient)
        to propagate trace context to Spring Boot microservices.
        """
        trace_id = trace_id_var.get() or cls.generate_trace_id()
        parent_span_id = span_id_var.get() or cls.generate_span_id()
        child_span_id = cls.generate_span_id()
        correlation_id = correlation_id_var.get() or cls.generate_correlation_id()
        txn_id = txn_id_var.get()

        headers = {
            HEADER_B3_TRACE_ID: trace_id,
            HEADER_B3_SPAN_ID: child_span_id,
            HEADER_B3_PARENT_SPAN_ID: parent_span_id,
            HEADER_B3_SAMPLED: "1",
            HEADER_CORRELATION_ID: correlation_id,
            HEADER_REQUEST_ID: request_id_var.get() or cls.generate_request_id()
        }
        if txn_id:
            headers[HEADER_TXN_ID] = txn_id
        return headers

def get_correlation_id() -> str:
    return correlation_id_var.get()

def get_trace_id() -> str:
    return trace_id_var.get()

def get_current_trace_id() -> str:
    return trace_id_var.get()

def get_span_id() -> str:
    return span_id_var.get()

def get_current_span_id() -> str:
    return span_id_var.get()

def get_request_id() -> str:
    return request_id_var.get()

def get_txn_id() -> str:
    return txn_id_var.get()
