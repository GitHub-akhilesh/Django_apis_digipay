import logging
from fastapi import APIRouter, WebSocket
from websocket.manager import WebSocketChatHandler

logger = logging.getLogger("ai_platform.api.routers.websocket")
router = APIRouter(tags=["WebSocket Chat"])

@router.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    """Establishes real-time connection."""
    await WebSocketChatHandler.handle_connection(websocket)
