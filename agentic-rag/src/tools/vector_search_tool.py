from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from src.rag.retrieval.retrieval_pipeline import (
    RetrievalPipeline,
    RetrievalPipelineResult,
)
from src.tools.base_tool import BaseTool, ToolCitation, ToolResult


class VectorSearchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(
        ...,
        min_length=1,
        description="Câu hỏi hoặc từ khóa cần tìm trong tài liệu nội bộ.",
    )


class VectorSearchTool(BaseTool):
    name = "vector_search"
    description = (
        "Tìm kiếm thông tin trong tài liệu nội bộ bằng vector/RAG search. "
        "Dùng khi cần tra cứu chính sách, nội quy, quy trình hoặc tài liệu đã index."
    )
    usage_hint = "Tìm nội quy, chính sách, quy định trong tài liệu."
    input_example = '{"query":"câu hỏi ngắn"}'
    args_schema = VectorSearchInput

    def __init__(
        self,
        retrieval_pipeline: RetrievalPipeline,
        allowed_role: str,
    ) -> None:
        self.retrieval_pipeline = retrieval_pipeline
        self.allowed_role = allowed_role

    async def run(self, query: str) -> ToolResult:
        query = query.strip()
        if not query:
            return ToolResult(
                observation="Không có truy vấn để tìm kiếm trong tài liệu nội bộ."
            )

        result = await self.retrieval_pipeline.retrieve_context(
            query=query,
            allowed_role=self.allowed_role,
        )

        if not result.used_context or not result.chunks:
            return ToolResult(
                observation="Không tìm thấy thông tin phù hợp trong tài liệu nội bộ.",
                used_context=False,
                low_confidence=result.low_confidence,
            )

        return ToolResult(
            observation=self._format_result(result),
            citations=[
                ToolCitation(
                    index=citation.index,
                    chunk_id=citation.chunk_id,
                    document_id=citation.document_id,
                    filename=citation.filename,
                    page=citation.page,
                    section=citation.section,
                    clause_number=citation.clause_number,
                    score=citation.score,
                    file_path=citation.file_path,
                )
                for citation in result.citations
            ],
            used_context=True,
            low_confidence=result.low_confidence,
            metadata={"tool": self.name},
        )

    def _format_result(self, result: RetrievalPipelineResult) -> str:
        citation_by_index = {
            citation.index: citation
            for citation in result.citations
        }

        lines = ["Kết quả tìm kiếm:"]

        for index, chunk in enumerate(result.chunks, start=1):
            citation = citation_by_index.get(index)
            filename = citation.filename if citation else chunk.filename
            page = citation.page if citation else chunk.page
            section = citation.section if citation else chunk.section
            clause_number = citation.clause_number if citation else chunk.clause_number

            source_parts = []
            if clause_number and section:
                source_parts.append(f"{clause_number} - {section}")
            elif clause_number:
                source_parts.append(clause_number)
            elif section:
                source_parts.append(section)
            source_parts.append(filename)
            if page:
                source_parts.append(f"Trang {page}")

            lines.extend(
                [
                    "",
                    f"[{index}] {' | '.join(source_parts)}",
                    chunk.content.strip(),
                ]
            )

        return "\n".join(lines)
