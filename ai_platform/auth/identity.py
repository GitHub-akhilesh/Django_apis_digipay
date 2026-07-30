"""
Bridging between DigiPay session tokens and this platform's identity model.

A real DigiPay session token looks like this:

    {
      "sub": "500100100014",
      "ownerId": "500100100014",
      "operatorIds": "500100100014,500100100022,500100100107",
      "roles": ["VLE", "ADMIN"],
      "txnId": "CZU1785383540756710ae63e4d6a41848ef",
      "iat": ..., "exp": ...
    }

It is signed with the shared JWT_SECRET, so it verifies here — but it differs
from what this platform originally assumed in three ways, each of which produced
a 401 or a silent authorisation failure:

  transport  DigiPay stores it in an `access_token` COOKIE. The middleware only
             read the Authorization header and a `?token=` query parameter, so a
             browser request carried no credential at all.
  identity   there is no `cscId`/`merchantId` claim; the CSC ID is in `ownerId`
             (falling back to `sub`). Without this the principal's merchant_id
             was empty, breaking tenant isolation and cscId injection.
  roles      DigiPay uses bare names like VLE and ADMIN; this platform's RBAC is
             written against ROLE_MERCHANT / ROLE_ADMIN and would deny everything.
"""

import logging
from typing import Any, Dict, List, Optional

from core.config import settings

logger = logging.getLogger("ai_platform.auth.identity")

# Claims that may carry the CSC ID, most specific first.
MERCHANT_ID_CLAIMS = ("cscId", "merchantId", "ownerId", "sub")

# Claims that may carry the acting user, most specific first.
USER_ID_CLAIMS = ("userId", "sub", "ownerId")

ROLE_PREFIX = "ROLE_"


def extract_token(request) -> Optional[str]:
    """
    Find the caller's token: Authorization header, then cookie, then query param.

    The cookie is what a browser actually sends for a DigiPay session; the header
    is what service-to-service callers and Swagger use.
    """
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        if token:
            return token

    for cookie_name in settings.jwt_cookie_names:
        token = request.cookies.get(cookie_name)
        if token:
            return token.strip()

    return request.query_params.get("token")


def extract_merchant_id(payload: Dict[str, Any]) -> str:
    """CSC ID of the account the caller acts for."""
    for claim in MERCHANT_ID_CLAIMS:
        value = payload.get(claim)
        if value:
            return str(value).strip()
    return ""


def extract_user_id(payload: Dict[str, Any]) -> str:
    for claim in USER_ID_CLAIMS:
        value = payload.get(claim)
        if value:
            return str(value).strip()
    return ""


def normalise_roles(raw_roles: Any) -> List[str]:
    """
    Translate DigiPay role names into this platform's ROLE_* vocabulary.

    The mapping is configuration (JWT_ROLE_MAP) because the meaning of a DigiPay
    role is a deployment decision, not a fact about the code — see the setting's
    documentation for why DigiPay's ADMIN is deliberately NOT mapped to
    ROLE_ADMIN by default.

    Unmapped names are passed through with a ROLE_ prefix so a new DigiPay role
    fails closed (no tool grants it) rather than being silently dropped.
    """
    if raw_roles is None:
        roles = []
    elif isinstance(raw_roles, str):
        roles = [part for part in raw_roles.replace(";", ",").split(",") if part.strip()]
    elif isinstance(raw_roles, (list, tuple, set)):
        roles = list(raw_roles)
    else:
        roles = [raw_roles]

    role_map = settings.jwt_role_map
    resolved: List[str] = []

    for role in roles:
        name = str(role).strip()
        if not name:
            continue
        mapped = role_map.get(name.upper())
        if mapped:
            resolved.append(mapped)
            continue
        if name.upper().startswith(ROLE_PREFIX):
            resolved.append(name.upper())
            continue
        # Unknown DigiPay role: keep it, prefixed, so it is visible in logs and
        # in the principal, but matches no tool's allow-list.
        logger.info(
            "Unmapped role %r on incoming token; passing through as %s%s. "
            "Add it to JWT_ROLE_MAP if it should grant access.",
            name, ROLE_PREFIX, name.upper()
        )
        resolved.append(f"{ROLE_PREFIX}{name.upper()}")

    # Preserve order, drop duplicates.
    seen = set()
    unique = []
    for role in resolved:
        if role not in seen:
            seen.add(role)
            unique.append(role)

    return unique or [settings.JWT_DEFAULT_ROLE]
