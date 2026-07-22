# DigiPay AI Platform Developer Guide

This guide details code standards and step-by-step extension instructions for developers.

---

## 1. Creating Custom Tools

To add a new tool to the system, follow these steps:

1. Create a function under the appropriate domain directory (e.g. `tools/wallet/new_tool.py`).
2. Annotate the function with the `@tool` decorator, providing a descriptive docstring and explicit arguments types.

Example:
```python
from tools.registry import tool

@tool
async def getNewStatus(merchant_id: str) -> str:
    """Queries status of merchant from Springfield gateway client."""
    return "ACTIVE"
```

## 2. Testing Your Changes

Make sure to add corresponding unit tests inside `tests/` and verify the whole suite passes before committing:
```bash
venv\Scripts\python -m pytest ai_platform/tests/ -v
```
