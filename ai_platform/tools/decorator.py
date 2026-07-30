import functools
import inspect
import logging
from typing import List, Callable, Optional, Dict, Any

from core.config import settings

logger = logging.getLogger("ai_platform.tools.decorator")

HEALTH_HEALTHY = "HEALTHY"
HEALTH_UNREACHABLE = "UNREACHABLE"

# Pre-existing tools whose paths come from settings.SERVICE_ENDPOINTS (/wallet,
# /merchant, /transaction, /ledger, /passbook, /aeps, /notification, /ticket)
# rather than the DigiPay Spring gateway's /v2/* controllers. The gateway does
# not serve those prefixes, so these return 401 and the assistant answers "I have
# flagged this for Level-2 human support" instead of the data.
#
# Resolved here, at registration, rather than by mutating the registry afterwards:
# re-running tool discovery rebuilds ToolMetadata objects, which silently reset an
# externally applied health flag back to HEALTHY.
LEGACY_MICROSERVICE_TOOLS = frozenset({
    "getWalletBalance",
    "getLimits",
    "getMerchantProfile",
    "getMerchantStatus",
    "getLedgerStatement",
    "getPassbook",
    "getTransaction",
    "balanceEnquiry",
    "cashWithdrawalStatus",
    "reverseTransaction",
    "sendAlert",
})


def resolve_health(name: str, declared_health: str) -> str:
    """UNREACHABLE when a tool's backing prefix is not served by the gateway."""
    if name in LEGACY_MICROSERVICE_TOOLS and not settings.LEGACY_MICROSERVICE_ENDPOINTS_ENABLED:
        return HEALTH_UNREACHABLE
    return declared_health

# Which backing system a tool reads from. Three distinct systems are in play, so
# the source is recorded per tool and surfaced by the governance API.
#
#   SOURCE_LEGACY       the original in-repo tool integrations, unchanged
#   SOURCE_GATEWAY_V2   Spring Boot gateway-service controllers (/v2/*, /v1/upi/*)
#   SOURCE_LEGACY_API   the separately deployed legacy DigiPay API service
#                       (app/main.py), called over HTTP on its own URLs
SOURCE_LEGACY = "legacy"
SOURCE_GATEWAY_V2 = "gateway_v2"
SOURCE_LEGACY_API = "legacy_digipay_api"

ALL_ROLES = ["ROLE_USER", "ROLE_MERCHANT", "ROLE_SUPPORT", "ROLE_ADMIN"]


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
        health: str = "HEALTHY",
        read_only: bool = True,
        domain: str = "general",
        source: str = SOURCE_LEGACY,
        endpoint: Optional[str] = None,
        requires_confirmation: bool = False,
        examples: Optional[List[str]] = None,
    ):
        self.name = name
        self.description = description
        self.func = func
        self.roles = roles or list(ALL_ROLES)
        self.cacheable = cacheable
        self.ttl = ttl
        self.timeout = timeout
        self.retries = retries
        self.version = version
        self.deprecated = deprecated
        self.owner = owner
        self.health = resolve_health(name, health)
        # read_only=False marks a tool whose backing API changes state. New
        # gateway-service integrations are read_only=True without exception;
        # the flag exists to describe the pre-existing tools accurately.
        self.read_only = read_only
        self.domain = domain
        self.source = source
        self.endpoint = endpoint
        self.requires_confirmation = requires_confirmation
        self.examples = examples or []
        self.required_args, self.optional_args = _split_args(func)

    @property
    def arg_names(self) -> List[str]:
        return self.required_args + self.optional_args

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "roles": self.roles,
            "domain": self.domain,
            "source": self.source,
            "endpoint": self.endpoint,
            "readOnly": self.read_only,
            "requiresConfirmation": self.requires_confirmation,
            "cacheable": self.cacheable,
            "ttl": self.ttl,
            "version": self.version,
            "deprecated": self.deprecated,
            "health": self.health,
            "owner": self.owner,
            "requiredArgs": self.required_args,
            "optionalArgs": self.optional_args,
            "examples": self.examples,
        }


def _split_args(func: Callable) -> tuple:
    """
    Derive required/optional argument names from the tool signature so the
    catalogue handed to the LLM never drifts from the actual implementation.
    """
    required: List[str] = []
    optional: List[str] = []
    try:
        signature = inspect.signature(func)
    except (TypeError, ValueError):
        return required, optional

    for name, param in signature.parameters.items():
        if name in ("jwt_token", "self", "kwargs", "args"):
            continue
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            continue
        camel = _to_camel(name)
        if param.default is inspect.Parameter.empty:
            required.append(camel)
        else:
            optional.append(camel)
    return required, optional


def _to_camel(snake: str) -> str:
    head, *rest = snake.split("_")
    return head + "".join(part.title() for part in rest)


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
    health: str = "HEALTHY",
    read_only: bool = True,
    domain: str = "general",
    source: str = SOURCE_LEGACY,
    endpoint: Optional[str] = None,
    requires_confirmation: bool = False,
    examples: Optional[List[str]] = None,
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
            health=health,
            read_only=read_only,
            domain=domain,
            source=source,
            endpoint=endpoint,
            requires_confirmation=requires_confirmation,
            examples=examples,
        )
        REGISTERED_TOOLS[name] = tool_meta

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        wrapper._tool_meta = tool_meta
        return wrapper
    return decorator
