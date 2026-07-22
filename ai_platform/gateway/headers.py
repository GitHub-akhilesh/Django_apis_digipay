from typing import Dict
from monitoring.mdc import TraceContext

def get_downstream_headers(extra_headers: Dict[str, str] = None) -> Dict[str, str]:
    """
    Combines active B3 tracing headers with caller extra headers
    for outgoing Spring Boot HTTP requests.
    """
    headers = TraceContext.current_headers()
    if extra_headers:
        headers.update(extra_headers)
    return headers
