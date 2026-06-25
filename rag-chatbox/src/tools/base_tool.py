from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCitation:
    index: int
    chunk_id: str
    filename: str
    score: float
    document_id: str | None = None
    page: int | None = None
    section: str | None = None
    clause_number: str | None = None
    file_path: str | None = None


@dataclass
class ToolResult:
    observation: str
    citations: list[ToolCitation] = field(default_factory=list)
    used_context: bool = False
    low_confidence: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseTool(ABC):
    name: str
    description: str  # LLM đọc cái này để biết chọn tool nào

    @abstractmethod
    async def run(self, **kwargs) -> str | ToolResult:
        """
        Thực thi tool và trả về observation string hoặc ToolResult có metadata.
        """
        pass

    def to_dict(self) -> dict:
        """Mô tả tool cho LLM đọc trong prompt."""
        return {
            "name": self.name,
            "description": self.description,
        }
