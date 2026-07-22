import json
import time
import asyncio
import logging
from typing import Dict, Any, List
from fastapi import WebSocket, WebSocketDisconnect

from auth.jwt import AuthManager
from memory.redis_memory import session_memory
from agent.orchestrator import AgentOrchestrator
from monitoring.prometheus import PlatformMetrics, TraceTracker

logger = logging.getLogger("ai_platform.websocket.manager")

class WebSocketChatHandler:
    @staticmethod
    async def handle_connection(websocket: WebSocket):
        await websocket.accept()
        logger.info("WebSocket handshake initiated.")
        
        token = websocket.query_params.get("token")
        csc_id = None
        roles = []
        try:
            csc_id = AuthManager.get_csc_id_from_ws_token(token)
            roles = AuthManager.get_roles_from_ws_token(token)
            logger.info(f"WebSocket client authenticated successfully. Merchant: {csc_id}")
            await websocket.send_json({
                "type": "status",
                "content": f"Connected as Merchant VLE {csc_id}"
            })
        except Exception as e:
            logger.warning(f"WebSocket auth failed: {e}. Closing socket.")
            await websocket.send_json({
                "type": "error",
                "content": f"Authentication failed: {str(e)}"
            })
            await websocket.close(code=1008)
            return

        try:
            while True:
                data = await websocket.receive_text()
                payload = json.loads(data)
                
                session_id = payload.get("sessionId") or "default_session"
                message = payload.get("message")
                
                if not message:
                    continue
                    
                logger.info(f"Received msg in session {session_id}: '{message}'")
                start_time = time.time()
                
                # Zipkin trace correlation
                trace_headers = TraceTracker.extract_or_generate_trace(websocket.headers)
                
                # Retrieve conversation history
                history = session_memory.get_history(session_id)
                
                await websocket.send_json({
                    "type": "status",
                    "content": "Analyzing query intent..."
                })
                await asyncio.sleep(0.3)
                
                try:
                    result = await AgentOrchestrator.chat(
                        session_id=session_id,
                        message=message,
                        csc_id=csc_id,
                        history=history,
                        user_roles=roles,
                        jwt_token=token
                    )
                    
                    intent = result["intent"]
                    response_text = result["response"]
                    escalate = result["escalate"]
                    policy_checked = result["policy_checked"]
                    
                    if intent in ["Wallet", "Refund", "Settlement", "KYC"]:
                        await websocket.send_json({
                            "type": "status",
                            "content": f"Orchestrating specialized {intent} tools..."
                        })
                        await asyncio.sleep(0.4)
                    
                    if escalate and "Warning" in response_text:
                        await websocket.send_json({
                            "type": "status",
                            "content": "Security check triggered a blocking event."
                        })
                        await asyncio.sleep(0.2)
                    
                    await websocket.send_json({
                        "type": "status",
                        "content": "Formulating final redacted response..."
                    })
                    await asyncio.sleep(0.2)
                    
                    # Stream tokens (words) to browser client
                    words = response_text.split(" ")
                    for i in range(len(words)):
                        chunk = words[i] + (" " if i < len(words) - 1 else "")
                        await websocket.send_json({
                            "type": "chunk",
                            "content": chunk
                        })
                        await asyncio.sleep(0.04)

                    # Terminal event
                    await websocket.send_json({
                        "type": "response",
                        "response": response_text,
                        "intent": intent,
                        "escalate": escalate,
                        "policyChecked": policy_checked
                    })
                    
                    # Save updated history
                    new_history = history + [
                        {"role": "user", "content": message},
                        {"role": "assistant", "content": response_text}
                    ]
                    session_memory.save_history(session_id, new_history)
                    
                    # Metrics recording
                    duration = time.time() - start_time
                    PlatformMetrics.record_request("/ws/chat", intent)
                    PlatformMetrics.record_latency("/ws/chat", duration)
                    if escalate:
                        PlatformMetrics.record_escalation()
                    PlatformMetrics.record_tokens("model-2.5-pro", len(message)//4, len(response_text)//4)

                except Exception as e:
                    logger.error(f"Error executing agent chat: {e}", exc_info=True)
                    PlatformMetrics.record_error("orchestration_failure")
                    await websocket.send_json({
                        "type": "error",
                        "content": f"Orchestration failure: {str(e)}"
                    })
                    
        except WebSocketDisconnect:
            logger.info(f"WebSocket client disconnected for cscId: {csc_id}")
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}", exc_info=True)
