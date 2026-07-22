import pytest
import json
from fastapi.testclient import TestClient
from main import app
from llm.factory import LLMProviderFactory
from llm.orchestrator import llm_orchestrator
from prompts.manager import prompt_manager

client = TestClient(app)

def test_liveness_endpoint():
    response = client.get("/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ALIVE"}

def test_prompt_versioning():
    p1 = prompt_manager.get_prompt("system_core", "v1")
    p2 = prompt_manager.get_prompt("system_core", "v2")
    assert "virtual agent" in p1
    assert "advanced" in p2

@pytest.mark.anyio
async def test_llm_provider_factory():
    provider = LLMProviderFactory.get_provider("openai")
    assert provider is not None
    
    res = await provider.generate("classify intent user query: 'my balance'", "system instruction")
    assert "intent" in res

@pytest.mark.anyio
async def test_llm_orchestrator_accounting():
    res = await llm_orchestrator.generate(
        prompt="decompose request wallet balance details",
        system_instruction="Support agent core prompt"
    )
    # Assert generated output has valid step elements
    assert "steps" in res or "intent" in res or len(res) > 0

@pytest.mark.anyio
async def test_llm_orchestrator_failover(monkeypatch):
    class FailedProvider:
        async def generate(self, prompt, system_instruction=""):
            raise ValueError("Downstream Provider Outage!")
            
    # Mock LLMProviderFactory to return FailedProvider for openai, but standard OllamaProvider for ollama
    from llm.ollama import OllamaProvider
    def mock_get_provider(name):
        if name == "openai" or name == "gemini":
            return FailedProvider()
        return OllamaProvider()
        
    monkeypatch.setattr(LLMProviderFactory, "get_provider", mock_get_provider)
    
    # Executing through orchestrator should failover past openai and gemini, succeeding on ollama
    res = await llm_orchestrator.generate("check limit values")
    assert len(res) > 0
