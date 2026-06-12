from pathlib import Path
from typing import Any

from src.rag.ingestion.loaders.base_loader import BaseLoader, Document
from src.rag.ingestion.loaders.pdf_loader import PDFLoader
from src.rag.ingestion.loaders.docx_loader import DocxLoader
from src.rag.ingestion.loaders.txt_loader import TxtLoader


class UnsupportedFileTypeError(ValueError):
    def __init__(self, extension: str, supported: list[str]):
        super().__init__(
            f"No loader registered for '{extension}'. "
            f"Supported: {supported}"
        )


class LoaderFactory:
    """
    Registry-based factory.

    Dùng registry thay vì if/elif vì:
    - Thêm loader mới không cần sửa factory (Open/Closed Principle)
    - Có thể list supported types ở runtime
    - Dễ mock trong tests

    Usage:
        docs = LoaderFactory.load(Path("noi_quy.pdf"), allowed_roles=allowed_roles)

        # Hoặc lấy loader instance nếu cần inspect:
        loader = LoaderFactory.get_loader(".pdf")
        docs = loader.load(path)

        # Đăng ký loader mới (e.g. xlsx):
        LoaderFactory.register(".xlsx", ExcelLoader)
    """

    # extension → loader class (chưa instantiate)
    _registry: dict[str, type[BaseLoader]] = {}

    @classmethod
    def register(cls, extension: str, loader_class: type[BaseLoader]) -> None:
        """Đăng ký loader cho một file extension."""
        ext = extension.lower()
        if not ext.startswith("."):
            ext = f".{ext}"
        cls._registry[ext] = loader_class

    @classmethod
    def get_loader(cls, extension: str) -> BaseLoader:
        """Trả về loader instance cho extension đã cho."""
        ext = extension.lower()
        if not ext.startswith("."):
            ext = f".{ext}"

        loader_class = cls._registry.get(ext)
        if loader_class is None:
            raise UnsupportedFileTypeError(
                extension=ext,
                supported=list(cls._registry.keys()),
            )
        return loader_class()

    @classmethod
    def load(
        cls,
        file_path: Path,
        allowed_roles: list[Any] | None = None,
    ) -> list[Document]:
        """
        Load file từ path, tự chọn loader phù hợp.
        Đây là method chính — hầu hết code sẽ gọi cái này.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        loader = cls.get_loader(file_path.suffix)
        return loader.load(file_path, allowed_roles=allowed_roles)

    @classmethod
    def supported_extensions(cls) -> list[str]:
        return list(cls._registry.keys())


# ── Đăng ký các loaders mặc định ─────────────────────────────────────────────
LoaderFactory.register(".pdf",  PDFLoader)
LoaderFactory.register(".docx", DocxLoader)
LoaderFactory.register(".txt",  TxtLoader)
