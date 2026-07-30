import re
from typing import Any, Dict, List

# Shown to end users, so the wording is plain rather than operational.
#
# This previously emitted "Sources & Provenance" with a section name and a
# "Confidence: 84%" score per chunk. Those are useful when tuning retrieval and
# meaningless to a VLE asking about a transaction limit — the score in particular
# invites the question "why is my answer only 76% right?", which is not what it
# measures. Retrieval scores remain available on the API response and in logs.
MAX_CITATIONS = 2

# ".pdf"/".md" and similar are an artefact of how the document is stored.
FILE_EXTENSION = re.compile(r"\.(pdf|md|docx?|txt)$", re.IGNORECASE)


class CitationEngine:
    @staticmethod
    def format_citations(retrieved_chunks: List[Dict[str, Any]]) -> str:
        """
        Append a short, human-readable source line to an answer.

        One or two documents with a page number is enough for a user to look
        something up or quote it to support; more becomes noise inside a chat
        bubble.
        """
        if not retrieved_chunks:
            return ""

        seen = set()
        sources = []
        for item in retrieved_chunks:
            name = str(item.get("source") or "").strip()
            if not name:
                continue
            title = FILE_EXTENSION.sub("", name).strip()
            page = item.get("page")
            label = f"{title} (page {page})" if page else title
            if label.lower() in seen:
                continue
            seen.add(label.lower())
            sources.append(label)
            if len(sources) >= MAX_CITATIONS:
                break

        if not sources:
            return ""

        prefix = "Source" if len(sources) == 1 else "Sources"
        return f"\n\n_{prefix}: " + "; ".join(sources) + "._"


citation_engine = CitationEngine()
