from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from src.rag.ingestion.loaders.base_loader import Document


@dataclass
class DocumentChunk:
    chunk_id: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseChunker(ABC):
    @abstractmethod
    def chunk(self, documents: list[Document]) -> list[DocumentChunk]:
        """
        Convert loaded Documents into smaller retrieval/indexing chunks.
        Loader loads. Chunker chunks.
        """
        ...