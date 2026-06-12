from pathlib import Path
from typing import Any

from src.rag.ingestion.loaders.base_loader import BaseLoader, Document

# Thứ tự thử encoding: UTF-8 trước, sau đó Windows Vietnamese (CP1258),
# sau đó Latin-1 làm fallback cuối cùng (không bao giờ raise UnicodeDecodeError)
_ENCODINGS = ["utf-8", "cp1258", "latin-1"]


class TxtLoader(BaseLoader):
    """
    Load plain text file.

    Split theo double newline (paragraph break).
    Mỗi paragraph = 1 Document, giữ nguyên thứ tự.

    Dùng cho: văn bản đã copy-paste từ web, export từ tools khác.
    """

    def load(
        self,
        file_path: Path,
        allowed_roles: list[Any] | None = None,
    ) -> list[Document]:
        content = self._read_with_encoding_fallback(file_path)

        # Split theo paragraph (2+ newlines liên tiếp)
        # strip từng paragraph, bỏ qua paragraph rỗng
        paragraphs = [
            p.strip()
            for p in content.split("\n\n")
            if p.strip()
        ]

        if not paragraphs:
            raise ValueError(f"'{file_path.name}' is empty.")

        return [
            Document(
                content=para,
                metadata=self._with_allowed_roles(
                    {
                        "source":       file_path.name,
                        "doc_type":     "txt",
                        "paragraph":    idx + 1,
                        "total_paras":  len(paragraphs),
                    },
                    allowed_roles,
                ),
            )
            for idx, para in enumerate(paragraphs)
        ]

    def _read_with_encoding_fallback(self, file_path: Path) -> str:
        for encoding in _ENCODINGS:
            try:
                return file_path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
        # Không bao giờ reach đây vì latin-1 decode được mọi byte
        raise ValueError(f"Cannot decode '{file_path.name}'")
