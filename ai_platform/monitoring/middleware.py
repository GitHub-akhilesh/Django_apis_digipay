from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from monitoring.mdc import (
    TraceContext,
    correlation_id_var,
    trace_id_var,
    span_id_var,
    parent_span_id_var,
    request_id_var,
    session_id_var,
    txn_id_var,
    merchant_id_var,
    client_ip_var,
    endpoint_var
)

class TracingMiddleware(BaseHTTPMiddleware):
    """
    HTTP Tracing Middleware implementing OpenZipkin Brave lifecycle steps:
    1. Parse incoming B3 headers via TraceContext.from_headers().
    2. Bind variables to thread-local ContextVar storage.
    3. Inject propagated trace headers back into outgoing response headers.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        client_host = request.client.host if request.client else "127.0.0.1"
        context = TraceContext.from_headers(
            headers=request.headers,
            client_host=client_host,
            endpoint_path=request.url.path
        )
        
        tokens = context.bind()
        try:
            response: Response = await call_next(request)
        finally:
            # Clean up context to avoid thread pollution across execution pools
            (t_corr, t_trace, t_span, t_parent, t_req, t_sess, t_txn, t_merch, t_ip, t_end) = tokens
            correlation_id_var.reset(t_corr)
            trace_id_var.reset(t_trace)
            span_id_var.reset(t_span)
            parent_span_id_var.reset(t_parent)
            request_id_var.reset(t_req)
            session_id_var.reset(t_sess)
            txn_id_var.reset(t_txn)
            merchant_id_var.reset(t_merch)
            client_ip_var.reset(t_ip)
            endpoint_var.reset(t_end)

        # Inject B3 propagation headers into outgoing HTTP response
        context.inject(response.headers)
        return response
