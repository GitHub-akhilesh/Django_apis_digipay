import functools
import logging
from typing import List, Callable, Optional, Dict, Any

logger = logging.getLogger("ai_platform.tools.decorator")

class ToolMetadata:
    def __init__(
        self,
        name: str,
        description: str,
        func: Callable,
        roles: List[str] = None,
        cacheable: bool = False,
        ttl: int = 30,
        timeout: int = 5,
        retries: int = 3,
        version: str = "1.0",
        deprecated: bool = False,
        owner: str = "DigiPay Platform Team",
        health: str = "HEALTHY"
    ):
        self.name = name
        self.description = description
        self.func = func
        self.roles = roles or ["ROLE_USER", "ROLE_MERCHANT", "ROLE_SUPPORT", "ROLE_ADMIN"]
        self.cacheable = cacheable
        self.ttl = ttl
        self.timeout = timeout
        self.retries = retries
        self.version = version
        self.deprecated = deprecated
        self.owner = owner
        self.health = health

REGISTERED_TOOLS: Dict[str, ToolMetadata] = {}

def tool(
    name: str,
    description: str,
    roles: List[str] = None,
    cacheable: bool = False,
    ttl: int = 30,
    timeout: int = 5,
    retries: int = 3,
    version: str = "1.0",
    deprecated: bool = False,
    owner: str = "DigiPay Platform Team",
    health: str = "HEALTHY"
):
    """Declarative decorator for tag-based tool registration."""
    def decorator(func: Callable):
        tool_meta = ToolMetadata(
            name=name,
            description=description,
            func=func,
            roles=roles,
            cacheable=cacheable,
            ttl=ttl,
            timeout=timeout,
            retries=retries,
            version=version,
            deprecated=deprecated,
            owner=owner,
            health=health
        )
        REGISTERED_TOOLS[name] = tool_meta
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
            
        wrapper._tool_meta = tool_meta
        return wrapper
    return decorator
