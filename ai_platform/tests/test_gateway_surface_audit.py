"""
Audit the chat-reachable API surface against the real Spring Boot controllers.

This is the standing guarantee behind the product rule that the assistant only
reads: no endpoint that moves money or changes state may ever be reachable from
chat. Reviewing safety.py by eye does not scale to 84 endpoints, so the same
check runs here.

The Java source is not part of this repository, so the controller-derived tests
skip when it is absent (CI, a fresh clone) and run for anyone who has the
gateway checked out alongside. The tests that need no Java always run.
"""
import os
import re

import pytest

from gateway.legacy_v1.client import EXCLUDED_ENDPOINTS as LEGACY_EXCLUDED
from gateway.legacy_v1.client import READ_ONLY_ENDPOINTS as LEGACY_READS
from gateway.v2.safety import ALLOWED_ENDPOINTS, EXCLUDED_ENDPOINTS

CONTROLLERS = os.environ.get(
    "DIGIPAY_GATEWAY_CONTROLLERS",
    r"D:\Office-Projects\DigiPay\digipay_setup\gateway-service"
    r"\src\main\java\com\digipay\gateway\controllers",
)

# Leading verb of the Java handler name. Judged on the prefix, not on a
# substring anywhere: fetchNotificationsLogin is a read even though it contains
# "login", while cancelServiceStatusSchedule is not.
WRITE_PREFIX = re.compile(
    r"^(create|update|insert|save|add|set|put|delete|remove|cancel|schedule|"
    r"initiate|process|submit|transfer|withdraw|deposit|refund|revers|topup|"
    r"payout|register|enable|disable|activate|deactivate|reset|change|upload|"
    r"generate|send|notify|perform|execute|apply|assign|approve|reject|block|"
    r"unblock|link|unlink|logout|login|authenticate)",
    re.I,
)

# Handlers whose name trips WRITE_PREFIX but which only read. Each is here
# because the service call it makes was checked by hand.
READ_DESPITE_NAME = {
    "recoveryList",              # ledgerService.recoveryList - a listing
    "scheduleList",              # listing
    "listServiceStatusSchedules",
    "blockHistory",
    "getBlockHistory",
}


def _strip_comments(src: str) -> str:
    """A //-disabled @GetMapping is not a live endpoint (see /v2/aeps/response)."""
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return re.sub(r"^\s*//.*$", "", src, flags=re.M)


def _balanced(src: str, i: int):
    """src[i] == '(' -> (inner, index_after_close), quote and nesting aware.

    Needed because @PreAuthorize("hasRole('ADMIN')") contains a ')': a lazy
    [^)]* pattern stops early and silently drops every annotated method.
    """
    depth, j, quote = 0, i, None
    while j < len(src):
        c = src[j]
        if quote:
            if c == quote and src[j - 1] != "\\":
                quote = None
        elif c in "\"'":
            quote = c
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return src[i + 1:j], j + 1
        j += 1
    return "", i + 1


_SIG = re.compile(r"\b(?:public|protected|private)\s+[\w<>,\[\]\s\.]+?\s+(\w+)\s*\(")
_CLS = re.compile(r'@RequestMapping\s*\(\s*(?:value\s*=\s*)?"([^"]*)"')
_ANN = re.compile(r"@(Get|Post|Put|Delete|Patch)Mapping")


def _live_endpoints():
    """[(controller, verb, path, handler)] for every live gateway endpoint."""
    out = []
    for fn in sorted(os.listdir(CONTROLLERS)):
        if not fn.endswith(".java"):
            continue
        with open(os.path.join(CONTROLLERS, fn), encoding="utf-8", errors="replace") as fh:
            src = _strip_comments(fh.read())
        m = _CLS.search(src)
        base = m.group(1) if m else ""
        for ann in _ANN.finditer(src):
            verb, k = ann.group(1).upper(), ann.end()
            args = ""
            if src[k:k + 1] == "(":
                args, k = _balanced(src, k)
            sub = (re.search(r'"([^"]*)"', args) or [None, ""])[1] if args else ""
            path = re.sub(r"/+", "/", f"{base.rstrip('/')}/{sub.lstrip('/')}") if sub else base
            path = path.rstrip("/") or base
            sig = _SIG.search(src, k)
            out.append((fn[:-5], verb, path, sig.group(1) if sig else "?"))
    return out


def _matches(spec_path: str, concrete: str) -> bool:
    pattern = "/".join(
        "[^/]+" if seg.startswith("{") and seg.endswith("}") else re.escape(seg)
        for seg in spec_path.split("/")
    )
    return re.fullmatch(pattern, concrete) is not None


requires_java = pytest.mark.skipif(
    not os.path.isdir(CONTROLLERS),
    reason=f"gateway Java source not present at {CONTROLLERS}",
)


# --------------------------------------------------------------------------
# Checks that need no Java source
# --------------------------------------------------------------------------

def test_allowed_and_excluded_do_not_overlap():
    allow = {(s.method, s.path) for s in ALLOWED_ENDPOINTS}
    deny = {(m, p) for m, p, _, _ in EXCLUDED_ENDPOINTS}
    assert not (allow & deny), f"endpoint both allowed and excluded: {allow & deny}"


def test_no_allowed_path_names_a_mutating_action():
    """Check the ACTION, which is the last real path segment - not a substring.

    On this gateway the action is the final segment: /v2/ledger/deposit acts,
    /v2/admin/dsp-wallet-transfer/logs reads. Substring matching cannot tell
    those apart ("transfer" appears in both) and yields false positives that
    invite exception lists; the terminal segment is unambiguous.
    """
    forbidden = {
        "deposit", "withdrawal", "withdraw", "transfer", "refund", "recovery",
        "init", "onboarding", "activate", "deactivate", "merchantcreation",
        "reqotp", "cancel", "schedule", "create", "update", "delete", "block",
        "unblock", "process", "topup", "payout", "login", "logout",
    }
    # A read verb anywhere in the path settles it, because the mutating word can
    # be a qualifier rather than the action: /v2/notification/fetch/login reads
    # the notifications shown on the login screen (fetchNotificationsLogin).
    read_markers = {
        "fetch", "list", "get", "log", "logs", "detail", "details", "status",
        "history", "report", "search", "balance", "response", "enquiry",
        "publickey", "check", "view", "download", "journey", "catalog",
        "analytics", "profiledetails", "orplist", "settlement", "operators",
    }
    for spec in ALLOWED_ENDPOINTS:
        segments = [s for s in spec.path.lower().split("/") if s and not s.startswith("{")]
        if read_markers & set(segments):
            continue
        action = segments[-1] if segments else ""
        assert action not in forbidden, \
            f"{spec.key} ends in the mutating action '{action}' but is allowed"


def test_legacy_reads_are_all_reads():
    for method, path, _ in LEGACY_READS:
        assert path in ("/txn-logs", "/passbook", "/wallet_balance", "/get-wallet-balance"), \
            f"unexpected legacy read endpoint {method} {path}"


def test_legacy_write_and_auth_endpoints_are_excluded():
    excluded = {p for _, p, _, _ in LEGACY_EXCLUDED}
    for path in ("/auth/token", "/agent/test-seed", "/chat", "/agent/chat"):
        assert path in excluded, f"{path} must be excluded from chat"


def test_legacy_lists_do_not_overlap():
    reads = {(m, p) for m, p, _ in LEGACY_READS}
    denies = {(m, p) for m, p, _, _ in LEGACY_EXCLUDED}
    assert not (reads & denies)


# --------------------------------------------------------------------------
# Checks against the real controllers
# --------------------------------------------------------------------------

@requires_java
def test_no_mutating_endpoint_is_reachable_from_chat():
    """The one that matters: nothing chat can call may change state."""
    allow = [(s.method, s.path) for s in ALLOWED_ENDPOINTS]
    offenders = []
    for _ctrl, verb, path, handler in _live_endpoints():
        reachable = any(m == verb and _matches(p, path) for m, p in allow)
        if reachable and WRITE_PREFIX.match(handler) and handler not in READ_DESPITE_NAME:
            offenders.append(f"{verb} {path} -> {handler}()")
    assert not offenders, "mutating endpoints reachable from chat: " + "; ".join(offenders)


@requires_java
def test_every_live_endpoint_is_classified():
    """safety.py claims to be the complete record of the gateway surface.

    An unclassified endpoint is not reachable (resolve_endpoint raises), so this
    is not a security hole - but it means the reviewable record has drifted from
    the controllers, which is how a new write endpoint gets missed.
    """
    allow = [(s.method, s.path) for s in ALLOWED_ENDPOINTS]
    deny = [(m, p) for m, p, _, _ in EXCLUDED_ENDPOINTS]
    unclassified = [
        f"{verb} {path} ({handler})"
        for _ctrl, verb, path, handler in _live_endpoints()
        if not any(m == verb and _matches(p, path) for m, p in allow + deny)
    ]
    assert not unclassified, "endpoints missing from safety.py: " + "; ".join(unclassified)


@requires_java
def test_no_allowed_endpoint_is_stale():
    """Every allowed path still exists in the controllers."""
    live = [(v, p) for _c, v, p, _h in _live_endpoints()]
    stale = [
        spec.key for spec in ALLOWED_ENDPOINTS
        if not any(v == spec.method and _matches(spec.path, p) for v, p in live)
    ]
    assert not stale, "allowed endpoints that no longer exist: " + "; ".join(stale)
