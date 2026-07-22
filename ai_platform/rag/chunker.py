import re
from typing import List, Dict, Any

class DocumentChunker:
    @staticmethod
    def chunk_document(
        content: str,
        source_name: str,
        chunk_size: int = 200,
        overlap: int = 40
    ) -> List[Dict[str, Any]]:
        """Splits document text into overlapping chunks with page/section anchors."""
        lines = content.split("\n")
        chunks = []
        current_chunk = []
        current_length = 0
        section_title = "General"
        page_number = 1

        for line in lines:
            if line.startswith("#"):
                section_title = line.lstrip("#").strip()
            page_match = re.search(r'Page\s*(\d+)', line, re.IGNORECASE)
            if page_match:
                page_number = int(page_match.group(1))

            words = line.split()
            current_chunk.extend(words)
            current_length += len(words)

            if current_length >= chunk_size:
                chunk_text = " ".join(current_chunk)
                chunks.append({
                    "text": chunk_text,
                    "source": source_name,
                    "section": section_title,
                    "page": page_number,
                    "chunk_id": f"{source_name}_p{page_number}_c{len(chunks)+1}"
                })
                # Preserve overlap
                current_chunk = current_chunk[-overlap:]
                current_length = len(current_chunk)

        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunks.append({
                "text": chunk_text,
                "source": source_name,
                "section": section_title,
                "page": page_number,
                "chunk_id": f"{source_name}_p{page_number}_c{len(chunks)+1}"
            })

        return chunks

document_chunker = DocumentChunker()
