import os
import json
import socket
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, UTC

from core.config import settings
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
    operation_var,
    client_ip_var,
    endpoint_var,
    latency_var,
    status_code_var,
    tool_var,
    intent_var,
    model_var,
    prompt_tokens_var,
    completion_tokens_var,
    cost_var,
    provider_var,
    cache_hit_var,
    retry_count_var
)

HOSTNAME = socket.gethostname()

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        latency_val = latency_var.get()
        latency_ms = round(latency_val * 1000, 2) if latency_val > 0.0 else 0.0

        log_payload = {
            "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "level": record.levelname,
            "logger": record.name,
            "service": service_name_var.get() or getattr(settings, "SERVICE_NAME", "AI_PLATFORM"),
            "channel": channel_var.get() or "DEFAULT",
            "operation": operation_var.get() or None,
            "environment": getattr(settings, "ENVIRONMENT", "local"),
            "version": getattr(settings, "APP_VERSION", "1.0.0"),
            "instance": HOSTNAME,
            "thread": record.threadName,
            "pid": os.getpid(),
            "correlationId": correlation_id_var.get() or None,
            "traceId": trace_id_var.get() or None,
            "spanId": span_id_var.get() or None,
            "parentId": parent_span_id_var.get() or None,
            "requestId": request_id_var.get() or None,
            "sessionId": session_id_var.get() or None,
            "txnId": txn_id_var.get() or None,
            "merchantId": merchant_id_var.get() or None,
            "userId": user_id_var.get() or None,
            "clientIP": client_ip_var.get() or None,
            "endpoint": endpoint_var.get() or None,
            "latency": latency_ms,
            "duration": f"{latency_ms}ms",
            "statusCode": status_code_var.get(),
            
            # AI Specific Metadata Fields for Telemetry
            "tool": tool_var.get() or None,
            "intent": intent_var.get() or None,
            "model": model_var.get() or None,
            "promptTokens": prompt_tokens_var.get() or None,
            "completionTokens": completion_tokens_var.get() or None,
            "cost": cost_var.get() or None,
            "provider": provider_var.get() or None,
            "cacheHit": cache_hit_var.get(),
            "retryCount": retry_count_var.get(),
            
            "message": record.getMessage()
        }

        if record.exc_info:
            log_payload["stacktrace"] = self.formatException(record.exc_info)

        return json.dumps(log_payload)

def configure_logging():
    root_logger = logging.getLogger()
    
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    formatter = JSONFormatter()

    # 1. Console Stream Handler
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)

    # 2. Rotating File Handler
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, "ai-platform.log")
    
    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Set log level
    log_level_str = getattr(settings, "LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    root_logger.setLevel(log_level)

    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
