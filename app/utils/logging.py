import logging
import uuid
from contextvars import ContextVar
from typing import Optional

# Correlation ID context variable
correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)

def get_correlation_id() -> str:
    val = correlation_id_var.get()
    if not val:
        val = str(uuid.uuid4())
        correlation_id_var.set(val)
    return val

def set_correlation_id(correlation_id: str) -> None:
    correlation_id_var.set(correlation_id)

class CorrelationFilter(logging.Filter):
    def filter(self, record):
        record.correlation_id = correlation_id_var.get() or "-"
        return True

def setup_logging():
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [correlation:%(correlation_id)s] [%(name)s] %(message)s'
    )
    
    root_logger = logging.getLogger()
    
    # Set standard logging configurations
    if not root_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        handler.addFilter(CorrelationFilter())
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)
    else:
        for handler in root_logger.handlers:
            handler.setFormatter(formatter)
            # Ensure correlation filter is added if not present
            if not any(isinstance(f, CorrelationFilter) for f in handler.filters):
                handler.addFilter(CorrelationFilter())
                
    # Suppress noise
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
