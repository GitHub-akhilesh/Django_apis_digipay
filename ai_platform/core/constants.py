# B3 Header Propagation Constants (Spring Boot Zipkin Sleuth / Micrometer)
HEADER_B3_TRACE_ID = "X-B3-TraceId"
HEADER_B3_SPAN_ID = "X-B3-SpanId"
HEADER_B3_PARENT_SPAN_ID = "X-B3-ParentSpanId"
HEADER_B3_SAMPLED = "X-B3-Sampled"

# Distributed Correlation & Business Context Headers
HEADER_CORRELATION_ID = "X-Correlation-ID"
HEADER_REQUEST_ID = "X-Request-ID"
HEADER_SESSION_ID = "X-Session-ID"
HEADER_TXN_ID = "X-Txn-ID"
HEADER_CSC_ID = "X-CSC-ID"

# Platform Core Constants
SERVICE_NAME = "ai-platform"
DEFAULT_SESSION_ID = "default_session"
DEFAULT_CSC_ID = "500100100014"

# Legacy aliases for backward compatibility
HEADER_TRACE_ID = HEADER_B3_TRACE_ID
HEADER_SPAN_ID = HEADER_B3_SPAN_ID
HEADER_SAMPLED = HEADER_B3_SAMPLED
