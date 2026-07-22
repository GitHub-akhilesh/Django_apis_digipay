from typing import List, Dict, Any

class CitationEngine:
    @staticmethod
    def format_citations(retrieved_chunks: List[Dict[str, Any]]) -> str:
        """Construct structured enterprise citations from retrieved knowledge chunks."""
        if not retrieved_chunks:
            return ""

        citation_lines = ["\n\n---"]
        citation_lines.append("**Sources & Provenance:**")
        
        for item in retrieved_chunks:
            source = item.get("source", "Knowledge Base")
            page = item.get("page", 1)
            section = item.get("section", "General")
            confidence = item.get("confidence_pct", 95)
            
            line = f"- 📄 **{source}** (Section: *{section}*, Page: {page}) — Confidence: **{confidence}%**"
            citation_lines.append(line)

        return "\n".join(citation_lines)

citation_engine = CitationEngine()
