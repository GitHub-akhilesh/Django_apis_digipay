import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from core.responses import ApiResponse
from admin.prompt_service import prompt_admin_service
from admin.provider_service import provider_admin_service
from admin.tool_service import tool_admin_service
from admin.conversation_service import conversation_admin_service
from admin.settings_service import settings_admin_service

logger = logging.getLogger("ai_platform.api.routers.admin")
router = APIRouter(prefix="/api/v1/admin", tags=["AI Admin Portal"])

class PromptUpdateRequest(BaseModel):
    key: str
    version: str
    template: str

class ProviderUpdateRequest(BaseModel):
    primary: str
    fallbacks: List[str]
    timeoutSeconds: int = 5

class ToolGovernanceRequest(BaseModel):
    roles: Optional[List[str]] = None
    health: Optional[str] = None
    deprecated: Optional[bool] = None

class FlagUpdateRequest(BaseModel):
    flagName: str
    enabled: bool

@router.get("/prompts")
async def get_prompts():
    """List system prompts and active versions."""
    return ApiResponse.respond_success(data=prompt_admin_service.get_all_prompts())

@router.put("/prompts")
async def update_prompt(req: PromptUpdateRequest):
    """Dynamically update system prompt template."""
    res = prompt_admin_service.update_prompt_template(req.key, req.version, req.template)
    return ApiResponse.respond_success(data=res, message="Prompt template updated.")

@router.get("/providers")
async def get_providers():
    """Get LLM provider configurations and fallback priority."""
    return ApiResponse.respond_success(data=provider_admin_service.get_provider_config())

@router.put("/providers")
async def update_providers(req: ProviderUpdateRequest):
    """Update LLM provider fallback priorities online."""
    res = provider_admin_service.update_provider_priorities(req.primary, req.fallbacks, req.timeoutSeconds)
    return ApiResponse.respond_success(data=res, message="Provider config updated.")

@router.get("/tools")
async def get_tools():
    """List registered tools and governance metadata."""
    return ApiResponse.respond_success(data=tool_admin_service.get_registered_tools())

@router.put("/tools/{name}")
async def update_tool(name: str, req: ToolGovernanceRequest):
    """Update tool governance roles, health, or deprecation status."""
    res = tool_admin_service.update_tool_governance(name, req.roles, req.health, req.deprecated)
    return ApiResponse.respond_success(data=res, message=f"Tool governance updated for {name}.")

@router.get("/conversations")
async def get_conversations():
    """List active sessions and conversation memory statistics."""
    res = await conversation_admin_service.get_active_sessions()
    return ApiResponse.respond_success(data=res)

@router.get("/conversations/{session_id}")
async def get_transcript(session_id: str):
    """Get transcript history for a session."""
    res = await conversation_admin_service.get_session_transcript(session_id)
    return ApiResponse.respond_success(data=res)

@router.get("/settings")
async def get_settings():
    """Get platform settings and feature flags."""
    return ApiResponse.respond_success(data=settings_admin_service.get_settings())

@router.put("/settings/flags")
async def update_flag(req: FlagUpdateRequest):
    """Toggle platform feature flags online."""
    res = settings_admin_service.update_feature_flag(req.flagName, req.enabled)
    return ApiResponse.respond_success(data=res, message=f"Feature flag {req.flagName} updated.")
