from typing import Optional
from monitoring.mdc import TraceContext

def add_business_tags(
    txn_id: Optional[str] = None,
    merchant_id: Optional[str] = None,
    user_id: Optional[str] = None,
    tool: Optional[str] = None,
    operation: Optional[str] = None
):
    """
    Enriches the active thread MDC context with business attributes
    without generating duplicate log lines.
    """
    TraceContext.process_txn(
        txn_id=txn_id,
        merchant_id=merchant_id,
        user_id=user_id,
        operation=operation or tool
    )
