"""
Chat message catalogue and renderer.

`tool_messages` holds the wording for every tool the assistant can run — what it
says while working, on success, when a result set is empty, when the backend
fails, and when the caller's role is not permitted. `formatter` turns a raw
gateway payload into the chat message described by that catalogue.
"""

from messaging.formatter import message_formatter
from messaging.tool_messages import TOOL_MESSAGES, ToolMessage, get_message

__all__ = ["TOOL_MESSAGES", "ToolMessage", "get_message", "message_formatter"]
