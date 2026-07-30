"""
Read-only client for the legacy DigiPay API service (`app/main.py`).

That service stays deployed separately on its own port with its own URLs, so
nothing any existing frontend calls changes. The AI platform simply talks to it
over HTTP like any other client, which is why this lives beside the
gateway-service clients rather than replacing anything.

Three envelope styles now exist in this codebase; keeping them in separate
modules is deliberate:

    gateway.base_client   {"success": bool, "data": ...}
    gateway.v2.base       CommonResponseBO {"status","msg","errors","resData"}
    gateway.legacy_v1     {"status","msg","errors","resData"} where resData is
                          BASE64-encoded JSON (app/schemas EnvelopedResponse)
"""

from gateway.legacy_v1.client import legacy_v1_client

__all__ = ["legacy_v1_client"]
