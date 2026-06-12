import re
from pathlib import Path
from typing import Any

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from src.rag.ingestion.loaders.base_loader import BaseLoader, Document

# Regex nhận diện ranh giới "Điều X" trong văn bản pháp luật VN
_DIEU_PATTERN = re.compile(r"(Điều\s+\d+[\.\:])", re.UNICODE)


class PDFLoader(BaseLoader):

    def load(
        self,
        file_path: Path,
        allowed_roles: list[Any] | None = None,
    ) -> list[Document]:
        try:
            reader = PdfReader(str(file_path))
        except PdfReadError as e:
            raise ValueError(f"Cannot read PDF '{file_path.name}': {e}") from e

        total_pages = len(reader.pages)
        docs: list[Document] = []

        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""

            if self._is_empty(text):
                continue

            # Detect xem trang này có "Điều X" không → thêm vào metadata
            # để chunker sau có thể dùng thông tin này
            dieu_matches = _DIEU_PATTERN.findall(text)

            docs.append(Document(
                content=text.strip(),
                metadata=self._with_allowed_roles(
                    {
                        "source":       file_path.name,
                        "doc_type":     "pdf",
                        "page":         page_num,
                        "total_pages":  total_pages,
                        # Danh sách các "Điều" xuất hiện trên trang, dùng để filter sau
                        "dieu_refs":    dieu_matches if dieu_matches else [],
                    },
                    allowed_roles,
                ),
            ))

        if not docs:
            raise ValueError(
                f"'{file_path.name}' appears to be a scanned PDF (no text layer). "
                "OCR is required for this file type."
            )

        return docs
