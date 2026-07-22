import time
import json
from dataclasses import dataclass
from typing import Dict, Any

class EventType:
    PLANNER_STARTED = "PlannerStarted"
    PLANNER_COMPLETED = "PlannerCompleted"
    TOOL_STARTED = "ToolStarted"
    TOOL_COMPLETED = "ToolCompleted"
    GATEWAY_STARTED = "GatewayStarted"
    GATEWAY_COMPLETED = "GatewayCompleted"
    LLM_STARTED = "LLMStarted"
    LLM_COMPLETED = "LLMCompleted"
    TOKEN_GENERATED = "TokenGenerated"
    CONVERSATION_COMPLETED = "ConversationCompleted"

@dataclass
class StreamEvent:
    event_type: str
    data: Dict[str, Any]
    timestamp: float = None

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()

    def to_sse(self) -> str:
        """Format as Server-Sent Events (SSE) data frame."""
        payload = {
            "event": self.event_type,
            "timestamp": self.timestamp,
            "data": self.data
        }
        return f"data: {json.dumps(payload)}\n\n"
