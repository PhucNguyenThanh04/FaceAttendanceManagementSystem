from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import unicodedata


@dataclass
class Document:
    """
    Output chuẩn của mọi loader.
    Chunker downstream chỉ cần biết về class này, không cần biết file gốc là gì.
    """
    content: str
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        # NFC normalization cho tiếng Việt
        # "ệ" có thể được encode là 1 code point (NFC) hoặc "e" + combining marks (NFD)
        # BGE-M3 tokenizer expect NFC → normalize ngay tại đây
        self.content = unicodedata.normalize("NFC", self.content)


class BaseLoader(ABC):

    @abstractmethod
    def load(
        self,
        file_path: Path,
        allowed_roles: list[Any] | None = None,
    ) -> list[Document]:
        """
        Load file, trả về list[Document].
        Mỗi Document là một đơn vị logic: 1 trang PDF, 1 section DOCX, v.v.
        KHÔNG chunk ở đây — chunker làm việc đó.
        """
        ...

    def _is_empty(self, text: str) -> bool:
        return not text or not text.strip()

    def _with_allowed_roles(
        self,
        metadata: dict[str, Any],
        allowed_roles: list[Any] | None,
    ) -> dict[str, Any]:
        return {
            **metadata,
            "allowed_roles": [
                role.value if hasattr(role, "value") else str(role)
                for role in (allowed_roles or [])
            ],
        }
