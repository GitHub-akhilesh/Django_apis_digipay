"""
Merge the legacy DigiPay service's OpenAPI schema into this service's schema.

Why
---
The legacy API (`app/main.py`) stays deployed as its own service on its own
original URLs, so no frontend has to change. But its endpoints were invisible in
this service's `/docs`, which made the platform look like it had lost them.

This module merges the legacy paths into the AI platform's schema so one Swagger
UI documents both APIs, while the routes are still served by two processes. Each
merged path carries an OpenAPI 3.1 per-path `servers` override so "Try it out"
hits the legacy service directly rather than 404-ing against this one.

That override uses `settings.legacy_api_public_url`, NOT LEGACY_API_URL: the
latter is the server-to-server address, which under Docker is the private
hostname `http://legacy-api:8000` that a browser on the host cannot resolve.

How the legacy schema is obtained
---------------------------------
By importing the legacy routers into a throwaway FastAPI instance - not over
HTTP. That keeps `/docs` working when the legacy service is down, avoids running
the legacy app's middleware and database setup as an import side effect, and
keeps the documentation deterministic.
"""

import logging
from typing import Any, Dict, Optional

from core.config import settings

logger = logging.getLogger("ai_platform.api.openapi_aggregate")

LEGACY_TAG = "Legacy DigiPay API (separate service)"

# Schema-component names get prefixed on collision so neither API's models are
# silently overwritten by the other's.
COMPONENT_PREFIX = "Legacy"

_cache: Optional[Dict[str, Any]] = None


def _build_legacy_schema() -> Optional[Dict[str, Any]]:
    """Generate the legacy service's OpenAPI schema from its routers."""
    try:
        # The legacy `app` package lives at the repository root, one level above
        # this service's own import root, so it has to be made importable here.
        import os
        import sys

        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if repo_root not in sys.path:
            sys.path.append(repo_root)

        from fastapi import FastAPI

        from app.routers.v1.agent import router as legacy_agent_router
        from app.routers.v1.endpoints import router as legacy_v1_router
    except Exception as e:
        logger.warning(
            f"Could not import the legacy routers to document them: {e}. "
            "The AI platform schema will not include the legacy API."
        )
        return None

    try:
        probe = FastAPI(
            title="DigiPay API Gateway & Ledger Services",
            version="1.0.0",
            # Mirrors app/main.py so the documented paths match what is served.
        )
        probe.include_router(legacy_v1_router, prefix=settings.LEGACY_API_PREFIX)
        probe.include_router(legacy_agent_router, prefix=settings.LEGACY_API_PREFIX)
        return probe.openapi()
    except Exception as e:
        logger.warning(f"Could not generate the legacy OpenAPI schema: {e}")
        return None


def _merge_components(target: Dict[str, Any], source: Dict[str, Any]) -> Dict[str, str]:
    """
    Copy the legacy schema components in, renaming on collision.

    Returns a map of old -> new component name so `$ref`s can be rewritten.
    """
    renames: Dict[str, str] = {}
    target_components = target.setdefault("components", {})

    for section, entries in (source.get("components") or {}).items():
        if not isinstance(entries, dict):
            continue
        target_section = target_components.setdefault(section, {})
        for name, definition in entries.items():
            final_name = name
            if name in target_section and target_section[name] != definition:
                final_name = f"{COMPONENT_PREFIX}{name}"
                # Extremely unlikely, but never overwrite a differing definition.
                suffix = 2
                while final_name in target_section and target_section[final_name] != definition:
                    final_name = f"{COMPONENT_PREFIX}{name}{suffix}"
                    suffix += 1
                renames[name] = final_name
            target_section[final_name] = definition

    return renames


def _rewrite_refs(node: Any, renames: Dict[str, str]) -> Any:
    """Recursively repoint $refs at any renamed components."""
    if not renames:
        return node
    if isinstance(node, dict):
        result = {}
        for key, value in node.items():
            if key == "$ref" and isinstance(value, str):
                for old, new in renames.items():
                    old_ref = f"/{old}"
                    if value.endswith(old_ref):
                        value = value[: -len(old_ref)] + f"/{new}"
                        break
            result[key] = _rewrite_refs(value, renames)
        return result
    if isinstance(node, list):
        return [_rewrite_refs(item, renames) for item in node]
    return node


def merge_legacy_openapi(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Return `schema` with the legacy service's paths merged in.

    Paths already present in this service are never overwritten - the AI
    platform's own `/api/v1/chat` keeps its definition rather than being replaced
    by the legacy alias of the same path.
    """
    global _cache

    if not settings.AGGREGATE_LEGACY_OPENAPI:
        return schema

    if _cache is None:
        _cache = _build_legacy_schema() or {}
    legacy = _cache
    if not legacy.get("paths"):
        return schema

    renames = _merge_components(schema, legacy)

    paths = schema.setdefault("paths", {})
    merged = 0
    skipped = []

    for path, operations in legacy["paths"].items():
        if path in paths:
            # A real collision: /api/v1/chat exists in both. Keep ours.
            skipped.append(path)
            continue

        operations = _rewrite_refs(operations, renames)

        for method, operation in operations.items():
            if not isinstance(operation, dict):
                continue
            operation["tags"] = [LEGACY_TAG]
            summary = operation.get("summary") or ""
            operation["summary"] = f"[Legacy service] {summary}".strip()
            description = operation.get("description") or ""
            operation["description"] = (
                f"{description}\n\n"
                f"**Served by the legacy DigiPay API service**, not by this one. "
                f"Base URL: `{settings.legacy_api_public_url}`. The URL path is unchanged."
            ).strip()

        # OpenAPI 3.1 per-path server override so "Try it out" reaches the
        # legacy service instead of 404-ing against this one.
        operations["servers"] = [{
            "url": settings.legacy_api_public_url,
            "description": "Legacy DigiPay API service",
        }]

        paths[path] = operations
        merged += 1

    if skipped:
        logger.info(
            "Legacy OpenAPI merge kept this service's definition for shared paths: %s",
            ", ".join(skipped),
        )

    tags = schema.setdefault("tags", [])
    if merged and not any(t.get("name") == LEGACY_TAG for t in tags):
        tags.append({
            "name": LEGACY_TAG,
            "description": (
                "Endpoints served by the separately deployed legacy DigiPay API service "
                f"at {settings.legacy_api_public_url}. Documented here for convenience; their URLs "
                "are unchanged and they are not handled by this service."
            ),
        })

    logger.info(f"Merged {merged} legacy API paths into the OpenAPI schema.")
    return schema


def reset_cache():
    """Drop the cached legacy schema (used by tests)."""
    global _cache
    _cache = None
