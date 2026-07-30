"""
Renders a raw gateway payload into the chat wording declared in
`messaging.tool_messages`.

The gateway's `resData` is not one fixed shape — some endpoints return an
object, some a bare list, and the paginated ones wrap rows under a key whose
name varies by controller. The formatter therefore probes for rows and counts
rather than assuming a schema, so a response that grows or renames fields
degrades to "show what is there" instead of failing.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from messaging.tool_messages import ToolMessage, get_message

logger = logging.getLogger("ai_platform.messaging.formatter")

# Keys that commonly hold the row collection in a paginated CommonResponseBO.
ROW_KEYS = (
    "list", "data", "rows", "records", "content", "items", "result", "results",
    "txnList", "logs", "details", "notifications", "operators", "devices",
    "services", "users", "entries", "passbook",
)

# Keys that commonly hold the total record count.
COUNT_KEYS = (
    "totalRecords", "totalRecord", "totalCount", "total", "totalElements",
    "count", "recordCount",
)

# Keys whose values are money and should render with a rupee symbol.
AMOUNT_KEY_PATTERN = re.compile(
    r"(amount|balance|amt|value|commission|charge|fee|credit|debit)$", re.IGNORECASE
)

# Keys that must never be echoed into a chat reply.
SENSITIVE_KEY_PATTERN = re.compile(
    r"(aadhaar|aadhar|uid|pid|pidData|biometric|password|pin|otp|token|secret|key|"
    r"certificate|encrypted|payload|signature)",
    re.IGNORECASE,
)

MAX_ROWS_RENDERED = 10
MAX_CELL_LENGTH = 42
MAX_COLUMNS_RENDERED = 7


class MessageFormatter:
    # ------------------------------------------------------------------ public

    def working(self, tool_name: str) -> str:
        return get_message(tool_name).working

    def denied(self, tool_name: str) -> str:
        return get_message(tool_name).denied

    def error(self, tool_name: str, detail: Optional[str] = None) -> str:
        msg = get_message(tool_name)
        text = msg.error
        if detail:
            text += f"\n\n_Details: {self._trim(detail, 220)}_"
        return text

    def render(self, tool_name: str, payload: Any) -> str:
        """Build the full chat message for a successful tool result."""
        msg = get_message(tool_name)

        rows, total, scalar = self._shape(payload)
        page, per_page = self._page_info(payload)

        if rows is not None:
            if not rows:
                return f"**{msg.label}**\n\n{msg.empty}"
            body = self._render_rows(msg, rows, total, page, per_page)
            return self._assemble(msg, body)

        if scalar is None or (isinstance(scalar, dict) and not scalar):
            return f"**{msg.label}**\n\n{msg.empty}"

        if isinstance(scalar, dict):
            body = self._render_object(msg, scalar)
        else:
            body = str(scalar)

        if not body.strip():
            return f"**{msg.label}**\n\n{msg.empty}"

        return self._assemble(msg, body)

    def summarise_outcomes(self, outcomes: List[Dict[str, Any]]) -> str:
        """
        Compose one reply covering every executed step. Used as the deterministic
        response when the model is unavailable, and as grounding for the model
        when it is.
        """
        sections: List[str] = []
        for outcome in outcomes:
            tool_name = outcome.get("tool", "")
            status = outcome.get("status")
            if status == "SUCCESS":
                sections.append(self.render(tool_name, outcome.get("result")))
            elif status == "PERMISSION_DENIED":
                sections.append(f"**{get_message(tool_name).label}**\n\n{self.denied(tool_name)}")
            elif status == "SESSION_EXPIRED":
                sections.append(
                    f"**{get_message(tool_name).label}**\n\n"
                    + (outcome.get("message")
                       or "Your DigiPay session has expired. Please sign in again "
                          "and ask me once more.")
                )
            elif status == "SECURITY_BLOCKED":
                sections.append(
                    f"**{get_message(tool_name).label}**\n\n"
                    + (outcome.get("message")
                       or "I stopped that lookup: the record does not belong to your account. "
                          "You can only view data for your own CSC ID.")
                )
            else:
                sections.append(self.error(tool_name, outcome.get("error")))
        return "\n\n---\n\n".join(sections)

    # ----------------------------------------------------------------- shaping

    @staticmethod
    def _page_info(payload: Any) -> Tuple[Optional[int], Optional[int]]:
        """Current page and page size, when the payload reports them."""
        if not isinstance(payload, dict):
            return None, None

        def as_int(*keys):
            for key in keys:
                value = payload.get(key)
                if isinstance(value, (int, float)):
                    return int(value)
                if isinstance(value, str) and value.isdigit():
                    return int(value)
            return None

        return as_int("currentPage", "cp", "page"), as_int("recordsPerPage", "rpp", "pageSize")

    def _shape(self, payload: Any) -> Tuple[Optional[List[Any]], Optional[int], Any]:
        """
        Classify a payload as (rows, total, scalar).

        Returns rows non-None when the payload is a collection — including an
        empty one, so "no records" is distinguishable from "not a list".
        """
        if payload is None:
            return None, None, None

        if isinstance(payload, list):
            return payload, len(payload), None

        if isinstance(payload, dict):
            total = next(
                (int(payload[k]) for k in COUNT_KEYS
                 if k in payload and isinstance(payload[k], (int, float))),
                None,
            )
            for key in ROW_KEYS:
                value = payload.get(key)
                if isinstance(value, list):
                    return value, (total if total is not None else len(value)), None
            # A dict of dicts with no scalar leaves is still a collection.
            return None, total, payload

        return None, None, payload

    # ---------------------------------------------------------------- rendering

    def _assemble(self, msg: ToolMessage, body: str) -> str:
        parts = [f"**{msg.label}**", "", msg.success, "", body]
        if msg.footnote:
            parts += ["", f"_{msg.footnote}_"]
        return "\n".join(parts)

    def _render_object(self, msg: ToolMessage, obj: Dict[str, Any]) -> str:
        """
        Declared fields first (good labels and ordering), then anything else the
        payload contains.

        The catalogue's field names are our best guess at the backend's response
        shape. When only some of them match, the rest of the payload must still be
        shown: a ledger balance whose amount is under a differently-named key
        rendered as nothing but "CSC ID: 500100100014" — technically a success,
        useless to the user. Never drop data just because it was not anticipated.
        """
        pairs = self._select_fields(msg.fields, obj)

        declared_keys = {key.lower() for _, key in msg.fields}
        declared_keys |= {
            re.sub(r"(?<!^)(?=[A-Z])", "_", key).lower() for _, key in msg.fields
        }
        # Also treat the keys already rendered as consumed, so nothing repeats.
        remaining = {
            key: value for key, value in obj.items()
            if key.lower() not in declared_keys
            and key.lower().replace("_", "") not in {k.replace("_", "") for k in declared_keys}
        }

        pairs += self._auto_fields(remaining, limit=12 - len(pairs))

        if not pairs:
            return ""
        return "\n".join(f"- **{label}:** {value}" for label, value in pairs)

    def _render_rows(
        self,
        msg: ToolMessage,
        rows: List[Any],
        total: Optional[int],
        page: Optional[int] = None,
        per_page: Optional[int] = None,
    ) -> str:
        shown = rows[:MAX_ROWS_RENDERED]

        # Rows may be plain strings (e.g. VPA suggestions).
        if all(not isinstance(r, dict) for r in shown):
            listing = "\n".join(f"- {self._trim(str(r), MAX_CELL_LENGTH)}" for r in shown)
            return self._with_row_count(listing, rows, total, page, per_page)

        dict_rows = [r for r in shown if isinstance(r, dict)]
        columns = self._select_columns(msg.row_fields, dict_rows)
        if not columns:
            return self._with_row_count(
                "\n".join(f"- {self._trim(str(r), 160)}" for r in dict_rows), rows, total, page, per_page
            )

        header = "| " + " | ".join(label for label, _ in columns) + " |"
        divider = "| " + " | ".join("---" for _ in columns) + " |"
        body_lines = []
        for row in dict_rows:
            cells = [
                self._trim(self._format_value(key, self._lookup(row, key)), MAX_CELL_LENGTH)
                for _, key in columns
            ]
            body_lines.append("| " + " | ".join(cells) + " |")

        table = "\n".join([header, divider] + body_lines)
        return self._with_row_count(table, rows, total, page, per_page)

    def _with_row_count(
        self,
        body: str,
        rows: List[Any],
        total: Optional[int],
        page: Optional[int] = None,
        per_page: Optional[int] = None,
    ) -> str:
        """
        Append the record count and, when there is more, how to reach it.

        The page number is stated explicitly and the next page named ("say 'page
        3'"), because "ask for the next page" alone gave the user no idea what to
        type — and with 728 passbook entries, paging is the normal case.
        """
        shown = len(rows[:MAX_ROWS_RENDERED])
        effective_total = total if total is not None else len(rows)

        if effective_total <= shown:
            label = "record" if effective_total == 1 else "records"
            return body + f"\n\n{effective_total} {label} in total."

        size = per_page or shown or MAX_ROWS_RENDERED
        current = page or 1
        first = (current - 1) * size + 1
        last = first + shown - 1
        total_pages = max(1, -(-effective_total // size))   # ceiling division

        body += (
            f"\n\nShowing {first}–{last} of {effective_total} "
            f"(page {current} of {total_pages})."
        )
        if current < total_pages:
            body += f" Say “page {current + 1}” for the next one, or give me a date range to narrow it down."
        else:
            body += " That is the last page."
        return body

    # ---------------------------------------------------------------- selection

    def _select_fields(
        self, specs: List[Tuple[str, str]], obj: Dict[str, Any]
    ) -> List[Tuple[str, str]]:
        pairs: List[Tuple[str, str]] = []
        for label, key in specs:
            value = self._lookup(obj, key)
            if value in (None, "", [], {}):
                continue
            pairs.append((label, self._format_value(key, value)))
        return pairs

    def _select_columns(
        self, specs: List[Tuple[str, str]], rows: List[Dict[str, Any]]
    ) -> List[Tuple[str, str]]:
        """
        Declared columns that rows actually populate, then any other populated keys.

        A partial match used to end the search: the ledger passbook declared six
        columns, only `txnDate` and `remarks` existed in the real payload, and the
        table rendered as "Date | Narration" — no amount, type or running balance,
        despite all three being present under different names. Appending the
        unmatched keys means a schema we guessed wrong still shows the data.
        """
        declared = [
            (label, key)
            for label, key in specs
            if any(self._lookup(row, key) not in (None, "") for row in rows)
        ]

        # Keys already covered, in every spelling the lookup accepts.
        covered = set()
        for _, key in specs:
            snake = re.sub(r"(?<!^)(?=[A-Z])", "_", key).lower()
            covered |= {key.lower(), snake, snake.replace("_", "")}

        extra: List[str] = []
        for row in rows:
            for key, value in row.items():
                flat = key.lower().replace("_", "")
                if flat in covered or key.lower() in covered:
                    continue
                if key in extra or SENSITIVE_KEY_PATTERN.search(key):
                    continue
                if isinstance(value, (dict, list)) or value in (None, ""):
                    continue
                extra.append(key)

        columns = declared + [(self._humanise(k), k) for k in extra]
        # A chat bubble cannot show twenty columns legibly.
        return columns[:MAX_COLUMNS_RENDERED]

    def _auto_fields(self, obj: Dict[str, Any], limit: int = 12) -> List[Tuple[str, str]]:
        """Render an unknown object shape by showing its scalar leaves."""
        pairs: List[Tuple[str, str]] = []
        if limit <= 0:
            return pairs
        for key, value in obj.items():
            if SENSITIVE_KEY_PATTERN.search(key):
                continue
            if isinstance(value, (dict, list)) or value in (None, ""):
                continue
            pairs.append((self._humanise(key), self._format_value(key, value)))
            if len(pairs) >= limit:
                break
        return pairs

    # ----------------------------------------------------------------- helpers

    @staticmethod
    def _lookup(obj: Dict[str, Any], key: str) -> Any:
        """Resolve a key across camelCase / snake_case / case-insensitive spellings."""
        if key in obj:
            return obj[key]
        snake = re.sub(r"(?<!^)(?=[A-Z])", "_", key).lower()
        if snake in obj:
            return obj[snake]
        lowered = {k.lower(): v for k, v in obj.items()}
        return lowered.get(key.lower()) or lowered.get(snake.replace("_", ""))

    @staticmethod
    def _humanise(key: str) -> str:
        spaced = re.sub(r"(?<!^)(?=[A-Z])", " ", key.replace("_", " ")).strip()
        return spaced[:1].upper() + spaced[1:]

    def _format_value(self, key: str, value: Any) -> str:
        if value is None:
            return "—"
        if isinstance(value, bool):
            return "Yes" if value else "No"
        if SENSITIVE_KEY_PATTERN.search(key):
            return "•••• (hidden)"
        if isinstance(value, (int, float)) and AMOUNT_KEY_PATTERN.search(key):
            return f"₹{value:,.2f}"
        if isinstance(value, str) and AMOUNT_KEY_PATTERN.search(key):
            try:
                return f"₹{float(value):,.2f}"
            except ValueError:
                return value
        if isinstance(value, (dict, list)):
            return self._trim(str(value), 120)
        return str(value)

    @staticmethod
    def _trim(text: str, limit: int) -> str:
        text = str(text).replace("\n", " ").replace("|", "\\|").strip()
        return text if len(text) <= limit else text[: limit - 1] + "…"


message_formatter = MessageFormatter()
