import pytest
import jwt
from datetime import datetime, UTC
from fastapi.testclient import TestClient
from main import app
from core.config import settings
from admin.prompt_service import prompt_admin_service
from admin.provider_service import provider_admin_service
from admin.tool_service import tool_admin_service
from admin.settings_service import settings_admin_service

client = TestClient(app)

def generate_admin_token() -> str:
    payload = {
        "sub": "adminuser",
        "cscId": "500100100014",
        "roles": ["ROLE_ADMIN"],
        "exp": int(datetime.now(UTC).timestamp()) + 3600
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def test_prompt_admin_service():
    prompts = prompt_admin_service.get_all_prompts()
    assert "availablePrompts" in prompts

    res = prompt_admin_service.update_prompt_template("CLASSIFIER", "v2.0", "New classifier template")
    assert res["status"] == "UPDATED"

def test_provider_admin_service():
    res = provider_admin_service.update_provider_priorities("gemini", ["openai", "ollama"], timeout=10)
    assert res["primaryProvider"] == "gemini"
    assert res["timeoutSeconds"] == 10
    
    # Restore provider configuration
    provider_admin_service.update_provider_priorities("openai", ["gemini", "ollama"], timeout=5)

def test_tool_admin_service():
    tools = tool_admin_service.get_registered_tools()
    assert tools["totalTools"] > 0

    upd = tool_admin_service.update_tool_governance("getWalletBalance", roles=["ROLE_ADMIN"])
    assert upd["roles"] == ["ROLE_ADMIN"]
    
    # Restore tool roles
    tool_admin_service.update_tool_governance("getWalletBalance", roles=["ROLE_USER", "ROLE_MERCHANT", "ROLE_SUPPORT", "ROLE_ADMIN"])

def test_settings_admin_service():
    res = settings_admin_service.update_feature_flag("enableSemanticMemory", False)
    assert res["enabled"] is False
    
    # Restore setting
    settings_admin_service.update_feature_flag("enableSemanticMemory", True)

def test_admin_rest_endpoints():
    token = generate_admin_token()
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Prompts GET
    r1 = client.get("/api/v1/admin/prompts", headers=headers)
    assert r1.status_code == 200

    # 2. Providers GET
    r2 = client.get("/api/v1/admin/providers", headers=headers)
    assert r2.status_code == 200

    # 3. Tools GET
    r3 = client.get("/api/v1/admin/tools", headers=headers)
    assert r3.status_code == 200

    # 4. Conversations GET
    r4 = client.get("/api/v1/admin/conversations", headers=headers)
    assert r4.status_code == 200

    # 5. Settings GET
    r5 = client.get("/api/v1/admin/settings", headers=headers)
    assert r5.status_code == 200
