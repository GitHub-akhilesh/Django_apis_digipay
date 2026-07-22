import logging
from typing import Dict, Any, List
from memory.redis_memory import session_memory
from agent.orchestrator import AgentOrchestrator
from core.config import settings

logger = logging.getLogger("ai_platform.services.chat_service")

class ChatService:
    async def get_session_history(self, session_id: str) -> List[Dict[str, str]]:
        return session_memory.get_history(session_id)

    async def process_chat_message(
        self, 
        session_id: str, 
        message: str, 
        csc_id: str, 
        user_roles: List[str] = None,
        jwt_token: str = None
    ) -> Dict[str, Any]:
        """
        Retrieves history, triggers LangGraph agent, saves updated context,
        and returns structured result.
        """
        logger.info(f"Processing message in chat service: session={session_id}")
        
        # 1. Fetch History
        history = session_memory.get_history(session_id)
        
        # 2. Invoke Orchestrator
        result = await AgentOrchestrator.chat(
            session_id=session_id,
            message=message,
            csc_id=csc_id,
            history=history,
            user_roles=user_roles,
            jwt_token=jwt_token
        )
        
        # 3. Update History
        new_history = history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": result["response"]}
        ]
        session_memory.save_history(session_id, new_history)
        
        # 4. Return result
        return {
            "response": result["response"],
            "intent": result["intent"],
            "escalate": result["escalate"],
            "policyChecked": result["policy_checked"]
        }

chat_service = ChatService()
