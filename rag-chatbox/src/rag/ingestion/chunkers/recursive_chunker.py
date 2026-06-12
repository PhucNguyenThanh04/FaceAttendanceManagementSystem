from __future__ import annotations

import re
# from dataclasses import replace
from typing import Any

from src.rag.ingestion.loaders.base_loader import Document
from src.rag.ingestion.chunkers.base_chunker import BaseChunker, DocumentChunk


class LegalStructureAwareChunker(BaseChunker):


    CLAUSE_PATTERN = re.compile(
        r"(?m)^(?P<number>\d+)\.\s+(?P<title>.+?)(?=\n\d+\.|\Z)",
        re.DOTALL,
    )

    POINT_PATTERN = re.compile(
        r"(?m)^(?P<label>[a-zA-ZđĐ])\)\s+(?P<body>.+?)(?=\n[a-zA-ZđĐ]\)|\Z)",
        re.DOTALL,
    )

    def __init__(
        self,
        max_chars: int = 2200,
        overlap_chars: int = 250,
        min_chars: int = 200,
    ) -> None:
        self.max_chars = max_chars
        self.overlap_chars = overlap_chars
        self.min_chars = min_chars

    def chunk(self, documents: list[Document]) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []

        for doc_index, document in enumerate(documents):
            section_chunks = self._chunk_one_document(document, doc_index)
            chunks.extend(section_chunks)

        return chunks

    def _chunk_one_document(
        self,
        document: Document,
        doc_index: int,
    ) -> list[DocumentChunk]:
        content = document.content.strip()
        metadata = dict(document.metadata)

        section_title = metadata.get("section") or ""
        heading_prefix = self._build_heading_prefix(metadata)

        # Nếu section ngắn, giữ nguyên 1 chunk.
        if len(content) <= self.max_chars:
            return [
                self._make_chunk(
                    content=f"{heading_prefix}\n\n{content}".strip(),
                    metadata={
                        **metadata,
                        "chunk_index": 0,
                        "chunk_level": "section",
                    },
                    doc_index=doc_index,
                    local_index=0,
                )
            ]

        # Nếu dài, thử chia theo Khoản.
        clause_blocks = self._split_by_clauses(content)

        if len(clause_blocks) > 1:
            result: list[DocumentChunk] = []

            for local_index, clause in enumerate(clause_blocks):
                clause_text = clause["text"].strip()
                clause_number = clause["number"]
                clause_title = clause["title"]

                clause_prefix = (
                    f"{heading_prefix}\n"
                    f"Khoản {clause_number}. {clause_title}"
                ).strip()

                if len(clause_text) <= self.max_chars:
                    result.append(
                        self._make_chunk(
                            content=f"{clause_prefix}\n\n{clause_text}".strip(),
                            metadata={
                                **metadata,
                                "chunk_index": local_index,
                                "chunk_level": "clause",
                                "clause_number": clause_number,
                                "clause_title": clause_title,
                            },
                            doc_index=doc_index,
                            local_index=local_index,
                        )
                    )
                else:
                    # Nếu Khoản vẫn dài, chia theo Điểm hoặc recursive.
                    sub_chunks = self._chunk_long_clause(
                        clause_text=clause_text,
                        prefix=clause_prefix,
                        base_metadata={
                            **metadata,
                            "chunk_level": "clause_part",
                            "clause_number": clause_number,
                            "clause_title": clause_title,
                        },
                        doc_index=doc_index,
                        start_index=local_index,
                    )
                    result.extend(sub_chunks)

            return result

        # Nếu không detect được Khoản, fallback recursive.
        texts = self._recursive_split(content)
        return [
            self._make_chunk(
                content=f"{heading_prefix}\n\n{text}".strip(),
                metadata={
                    **metadata,
                    "chunk_index": i,
                    "chunk_level": "recursive",
                },
                doc_index=doc_index,
                local_index=i,
            )
            for i, text in enumerate(texts)
        ]

    def _chunk_long_clause(
        self,
        clause_text: str,
        prefix: str,
        base_metadata: dict[str, Any],
        doc_index: int,
        start_index: int,
    ) -> list[DocumentChunk]:
        point_blocks = self._split_by_points(clause_text)

        if len(point_blocks) > 1:
            chunks: list[DocumentChunk] = []

            for i, point in enumerate(point_blocks):
                point_label = point["label"]
                point_text = point["text"].strip()

                if len(point_text) <= self.max_chars:
                    parts = [point_text]
                else:
                    parts = self._recursive_split(point_text)

                for j, part in enumerate(parts):
                    local_index = start_index * 100 + i * 10 + j
                    chunks.append(
                        self._make_chunk(
                            content=(
                                f"{prefix}\n"
                                f"Điểm {point_label})\n\n"
                                f"{part}"
                            ).strip(),
                            metadata={
                                **base_metadata,
                                "chunk_index": local_index,
                                "point_label": point_label,
                            },
                            doc_index=doc_index,
                            local_index=local_index,
                        )
                    )

            return chunks

        # Không detect được điểm thì recursive split.
        texts = self._recursive_split(clause_text)

        return [
            self._make_chunk(
                content=f"{prefix}\n\n{text}".strip(),
                metadata={
                    **base_metadata,
                    "chunk_index": start_index * 100 + i,
                },
                doc_index=doc_index,
                local_index=start_index * 100 + i,
            )
            for i, text in enumerate(texts)
        ]

    def _split_by_clauses(self, text: str) -> list[dict[str, str]]:
        matches = list(self.CLAUSE_PATTERN.finditer(text))

        blocks: list[dict[str, str]] = []

        for match in matches:
            number = match.group("number").strip()
            raw_title_and_body = match.group("title").strip()

            first_line, body = self._split_first_line(raw_title_and_body)

            blocks.append(
                {
                    "number": number,
                    "title": first_line,
                    "text": f"{number}. {raw_title_and_body}",
                }
            )

        return blocks

    def _split_by_points(self, text: str) -> list[dict[str, str]]:
        matches = list(self.POINT_PATTERN.finditer(text))

        blocks: list[dict[str, str]] = []

        for match in matches:
            label = match.group("label").strip()
            body = match.group("body").strip()

            blocks.append(
                {
                    "label": label,
                    "text": f"{label}) {body}",
                }
            )

        return blocks

    def _recursive_split(self, text: str) -> list[str]:
        text = text.strip()

        if len(text) <= self.max_chars:
            return [text]

        chunks: list[str] = []
        start = 0

        while start < len(text):
            end = min(start + self.max_chars, len(text))
            window = text[start:end]

            split_at = self._find_best_split(window)

            if split_at <= 0:
                split_at = len(window)

            chunk = window[:split_at].strip()

            if chunk:
                chunks.append(chunk)

            if end >= len(text):
                break

            start = start + max(split_at - self.overlap_chars, 1)

        return chunks

    def _find_best_split(self, text: str) -> int:
        separators = ["\n\n", "\n", ". ", "; ", ", ", " "]

        for sep in separators:
            index = text.rfind(sep)
            if index > self.min_chars:
                return index + len(sep)

        return len(text)

    def _build_heading_prefix(self, metadata: dict[str, Any]) -> str:
        parts: list[str] = []

        source = metadata.get("source")
        section = metadata.get("section")

        if source:
            parts.append(f"Tài liệu: {source}")

        if section:
            parts.append(str(section))

        return "\n".join(parts).strip()

    def _split_first_line(self, text: str) -> tuple[str, str]:
        lines = text.splitlines()

        if not lines:
            return "", ""

        first_line = lines[0].strip()
        rest = "\n".join(lines[1:]).strip()

        return first_line, rest

    def _make_chunk(
        self,
        content: str,
        metadata: dict[str, Any],
        doc_index: int,
        local_index: int,
    ) -> DocumentChunk:
        source = metadata.get("source", "unknown")
        section_index = metadata.get("section_index", doc_index)

        chunk_id = f"{source}::section_{section_index}::chunk_{local_index}"

        return DocumentChunk(
            chunk_id=chunk_id,
            content=content,
            metadata=metadata,
        )