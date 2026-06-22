from __future__ import annotations

from fastapi import Depends

from src.core.dependenci import (
    get_retrieval_pipeline,
)
from src.features.chat.schemas import (
    ChatCitation,
    ChatRequest,
    ChatResponse,
)
from src.integrations.llm.client import GeminiClient, get_gemini_client
from src.integrations.llm.prompts import (
    PromptBuilder,
    RAG_SYSTEM_PROMPT,
)
from src.rag.retrieval.context_builder import ContextCitation
from src.rag.retrieval.retrieval_pipeline import RetrievalPipeline


NO_CONTEXT_ANSWER = "Không tìm thấy thông tin phù hợp trong tài liệu nội bộ."
LOW_CONFIDENCE_INSTRUCTION = (
    "Nếu trả lời được, hãy nói rõ rằng thông tin tìm thấy có thể chưa đầy đủ "
    "vì chỉ có ít tài liệu liên quan."
)


class ChatService:
    def __init__(
        self,
        retrieval_pipeline: RetrievalPipeline,
        llm_client: GeminiClient,
    ) -> None:
        self.retrieval_pipeline = retrieval_pipeline
        self.llm_client = llm_client

    async def chat(self, request: ChatRequest) -> ChatResponse:
        retrieval_result = await self.retrieval_pipeline.retrieve_context(
            query=request.message,
            allowed_role=request.role,
        )

        if not retrieval_result.used_context:
            return self._no_context_response()

        prompt = PromptBuilder.build_rag_prompt(
            question=request.message,
            chunks=retrieval_result.chunks,
            history=request.chat_history,
        )
        if retrieval_result.low_confidence:
            prompt = f"{prompt}\n\n{LOW_CONFIDENCE_INSTRUCTION}"

        llm_response = await self.llm_client.generate(
            prompt=prompt,
            system_prompt=RAG_SYSTEM_PROMPT,
        )

        return ChatResponse(
            answer=llm_response.content,
            citations=[
                self._to_chat_citation(citation)
                for citation in retrieval_result.citations
            ],
            low_confidence=retrieval_result.low_confidence,
            used_context=True,
        )

    def _no_context_response(self) -> ChatResponse:
        return ChatResponse(
            answer=NO_CONTEXT_ANSWER,
            citations=[],
            low_confidence=False,
            used_context=False,
        )

    @staticmethod
    def _to_chat_citation(citation: ContextCitation) -> ChatCitation:
        return ChatCitation(
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


def get_chat_service(
    retrieval_pipeline: RetrievalPipeline = Depends(get_retrieval_pipeline),
) -> ChatService:
    return ChatService(
        retrieval_pipeline=retrieval_pipeline,
        llm_client=get_gemini_client(),
    )
