import uuid
from typing import Dict, Optional, Any
from contextvars import ContextVar
from core.constants import (
    HEADER_B3_TRACE_ID,
    HEADER_B3_SPAN_ID,
    HEADER_B3_PARENT_SPAN_ID,
    HEADER_B3_SAMPLED,
    HEADER_CORRELATION_ID,
    HEADER_REQUEST_ID,
    HEADER_TXN_ID,
    HEADER_CSC_ID
)

# Thread-safe ContextVars (Direct Java SLF4J MDC equivalent for Python)
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")
span_id_var: ContextVar[str] = ContextVar("span_id", default="")
parent_span_id_var: ContextVar[str] = ContextVar("parent_span_id", default="")
request_id_var: ContextVar[str] = ContextVar("request_id", default="")
session_id_var: ContextVar[str] = ContextVar("session_id", default="")
txn_id_var: ContextVar[str] = ContextVar("txn_id", default="")
merchant_id_var: ContextVar[str] = ContextVar("merchant_id", default="")
user_id_var: ContextVar[str] = ContextVar("user_id", default="")
service_name_var: ContextVar[str] = ContextVar("service_name", default="AI_PLATFORM")
channel_var: ContextVar[str] = ContextVar("channel", default="DEFAULT")
tenant_id_var: ContextVar[str] = ContextVar("tenant_id", default="")
operation_var: ContextVar[str] = ContextVar("operation", default="")
client_ip_var: ContextVar[str] = ContextVar("client_ip", default="")
endpoint_var: ContextVar[str] = ContextVar("endpoint", default="")
latency_var: ContextVar[float] = ContextVar("latency", default=0.0)
status_code_var: ContextVar[int] = ContextVar("status_code", default=200)

# AI specific observability parameters
tool_var: ContextVar[str] = ContextVar("tool", default="")
intent_var: ContextVar[str] = ContextVar("intent", default="")
model_var: ContextVar[str] = ContextVar("model", default="")
prompt_tokens_var: ContextVar[int] = ContextVar("prompt_tokens", default=0)
completion_tokens_var: ContextVar[int] = ContextVar("completion_tokens", default=0)
cost_var: ContextVar[float] = ContextVar("cost", default=0.0)
provider_var: ContextVar[str] = ContextVar("provider", default="")
cache_hit_var: ContextVar[bool] = ContextVar("cache_hit", default=False)
retry_count_var: ContextVar[int] = ContextVar("retry_count", default=0)

HEADER_CORRELATION_ID = "X-Correlation-ID"
HEADER_REQUEST_ID = "X-Request-ID"

class TraceContext:
    """
    Tracing Context Manager matching OpenZipkin Brave / Spring Sleuth standards.
    Handles HTTP header extraction, context binding, and header injection.
    """
    def __init__(
        self,
        trace_id: str,
        span_id: str,
        parent_span_id: str = "",
        correlation_id: str = "",
        request_id: str = "",
        session_id: str = "",
        txn_id: str = "",
        merchant_id: str = "",
        client_ip: str = "127.0.0.1",
        endpoint: str = "/"
    ):
        self.trace_id = trace_id
        self.span_id = span_id
        self.parent_span_id = parent_span_id
        self.correlation_id = correlation_id or f"corr-{uuid.uuid4().hex[:12]}"
        self.request_id = request_id or f"req-{uuid.uuid4().hex[:12]}"
        self.session_id = session_id
        self.txn_id = txn_id
        self.merchant_id = merchant_id
        self.client_ip = client_ip
        self.endpoint = endpoint

    @classmethod
    def from_headers(cls, headers: Any, client_host: str = "127.0.0.1", endpoint_path: str = "/") -> "TraceContext":
        """
        Factory creating a TraceContext by parsing incoming B3 propagation headers from Spring API Gateway.
        """
        b3_trace = headers.get(HEADER_B3_TRACE_ID) or headers.get(HEADER_B3_TRACE_ID.lower())
        b3_span = headers.get(HEADER_B3_SPAN_ID) or headers.get(HEADER_B3_SPAN_ID.lower())
        b3_parent = headers.get(HEADER_B3_PARENT_SPAN_ID) or headers.get(HEADER_B3_PARENT_SPAN_ID.lower())
        corr_id = headers.get(HEADER_CORRELATION_ID) or headers.get(HEADER_CORRELATION_ID.lower())
        req_id = headers.get(HEADER_REQUEST_ID) or headers.get(HEADER_REQUEST_ID.lower())
        sess_id = headers.get("X-Session-ID") or headers.get("x-session-id") or ""
        txn_id = headers.get(HEADER_TXN_ID) or headers.get(HEADER_TXN_ID.lower()) or ""
        merchant_id = headers.get(HEADER_CSC_ID) or headers.get(HEADER_CSC_ID.lower()) or ""

        trace_id = b3_trace or uuid.uuid4().hex
        parent_id = b3_parent or (b3_span if b3_trace else "")
        span_id = uuid.uuid4().hex[:16]

        return cls(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_id,
            correlation_id=corr_id,
            request_id=req_id,
            session_id=sess_id,
            txn_id=txn_id,
            merchant_id=merchant_id,
            client_ip=client_host,
            endpoint=endpoint_path
        )

    def bind(self) -> tuple:
        """Binds context attributes into ContextVar thread memory."""
        t_corr = correlation_id_var.set(self.correlation_id)
        t_trace = trace_id_var.set(self.trace_id)
        t_span = span_id_var.set(self.span_id)
        t_parent = parent_span_id_var.set(self.parent_span_id)
        t_req = request_id_var.set(self.request_id)
        t_sess = session_id_var.set(self.session_id)
        t_txn = txn_id_var.set(self.txn_id)
        t_merch = merchant_id_var.set(self.merchant_id)
        t_ip = client_ip_var.set(self.client_ip)
        t_end = endpoint_var.set(self.endpoint)
        return (t_corr, t_trace, t_span, t_parent, t_req, t_sess, t_txn, t_merch, t_ip, t_end)

    def inject(self, target_headers: Any):
        """Injects current B3 propagation and correlation headers into outgoing response or client headers."""
        target_headers[HEADER_B3_TRACE_ID] = self.trace_id
        target_headers[HEADER_B3_SPAN_ID] = self.span_id
        if self.parent_span_id:
            target_headers[HEADER_B3_PARENT_SPAN_ID] = self.parent_span_id
        target_headers[HEADER_B3_SAMPLED] = "1"
        target_headers[HEADER_CORRELATION_ID] = self.correlation_id
        target_headers[HEADER_REQUEST_ID] = self.request_id
        if self.txn_id:
            target_headers[HEADER_TXN_ID] = self.txn_id

    @staticmethod
    def process_txn(
        txn_id: Optional[str] = None,
        merchant_id: Optional[str] = None,
        service: Optional[str] = None,
        channel: Optional[str] = None,
        operation: Optional[str] = None,
        user_id: Optional[str] = None,
        tool: Optional[str] = None,
        intent: Optional[str] = None,
        model: Optional[str] = None,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        cost: Optional[float] = None,
        provider: Optional[str] = None,
        cache_hit: Optional[bool] = None,
        retry_count: Optional[int] = None
    ):
        """
        Mirrors Spring Boot ZipKinUtils.processTxn(txnId, cscId, service) exactly.
        Binds business-level transaction attributes into MDC context variables.
        """
        if txn_id:
            txn_id_var.set(txn_id)
        if merchant_id:
            merchant_id_var.set(merchant_id)
        if service:
            service_name_var.set(service)
        if channel:
            channel_var.set(channel)
        if operation:
            operation_var.set(operation)
        if user_id:
            user_id_var.set(user_id)
        if tool:
            tool_var.set(tool)
        if intent:
            intent_var.set(intent)
        if model:
            model_var.set(model)
        if prompt_tokens is not None:
            prompt_tokens_var.set(prompt_tokens)
        if completion_tokens is not None:
            completion_tokens_var.set(completion_tokens)
        if cost is not None:
            cost_var.set(cost)
        if provider:
            provider_var.set(provider)
        if cache_hit is not None:
            cache_hit_var.set(cache_hit)
        if retry_count is not None:
            retry_count_var.set(retry_count)

    @staticmethod
    def clear():
        """
        Mirrors Spring Boot ZipKinUtils.clearMdc() exactly.
        Clears business transaction context variables from MDC thread storage.
        """
        txn_id_var.set("")
        merchant_id_var.set("")
        operation_var.set("")
        tool_var.set("")
        intent_var.set("")
        model_var.set("")
        prompt_tokens_var.set(0)
        completion_tokens_var.set(0)
        cost_var.set(0.0)
        provider_var.set("")
        cache_hit_var.set(False)
        retry_count_var.set(0)

    @classmethod
    def current_headers(cls) -> Dict[str, str]:
        """Returns active B3 propagation headers for downstream calls."""
        trace_id = trace_id_var.get() or uuid.uuid4().hex
        span_id = span_id_var.get() or uuid.uuid4().hex[:16]
        headers = {
            HEADER_B3_TRACE_ID: trace_id,
            HEADER_B3_SPAN_ID: uuid.uuid4().hex[:16],
            HEADER_B3_PARENT_SPAN_ID: span_id,
            HEADER_B3_SAMPLED: "1",
            HEADER_CORRELATION_ID: correlation_id_var.get() or f"corr-{uuid.uuid4().hex[:12]}",
            HEADER_REQUEST_ID: request_id_var.get() or f"req-{uuid.uuid4().hex[:12]}"
        }
        if txn_id_var.get():
            headers[HEADER_TXN_ID] = txn_id_var.get()
        return headers

    @classmethod
    def get_b3_headers(cls) -> Dict[str, str]:
        """Backward-compatible alias for current_headers()."""
        return cls.current_headers()


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
