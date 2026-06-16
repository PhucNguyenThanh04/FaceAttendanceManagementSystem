from __future__ import annotations

from fastapi import Depends

from src.core.dependenci import (
    get_embedding_service,
    get_reranker_service,
    get_vector_store,
)
from src.core.settings import settings
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
from src.integrations.qdrant.store import QdrantSearchResult, QdrantVectorStore
from src.rag.embeddings.embedding_service import EmbeddingService
from src.rag.retrieval.context_builder import ContextBuilder, ContextCitation
from src.rag.retrieval.hybrid_retriever import HybridRetriever
from src.rag.retrieval.reranker import RerankerService


NO_CONTEXT_ANSWER = "Không tìm thấy thông tin phù hợp trong tài liệu nội bộ."
SCORE_SPREAD_THRESHOLD = 0.3
TOP_SCORE_WINDOW = 0.1
LOW_CONFIDENCE_INSTRUCTION = (
    "Nếu trả lời được, hãy nói rõ rằng thông tin tìm thấy có thể chưa đầy đủ "
    "vì chỉ có ít tài liệu liên quan."
)


class ChatService:
    def __init__(
        self,
        hybrid_retriever: HybridRetriever,
        reranker_service: RerankerService,
        context_builder: ContextBuilder,
        llm_client: GeminiClient,
    ) -> None:
        self.hybrid_retriever = hybrid_retriever
        self.reranker_service = reranker_service
        self.context_builder = context_builder
        self.llm_client = llm_client

    async def chat(self, request: ChatRequest) -> ChatResponse:
        retrieved_results = await self.hybrid_retriever.retrieve(
            query=request.question,
            allowed_role=request.user_role,
        )

        reranked_results = await self.reranker_service.rerank(
            query=request.question,
            results=retrieved_results,
        )

        qualified_results = self._filter_quality(reranked_results)
        if not qualified_results:
            return self._no_context_response()

        low_confidence = len(qualified_results) == 1
        context_result = self.context_builder.build(qualified_results)

        if not context_result.chunks:
            return self._no_context_response()

        prompt = PromptBuilder.build_rag_prompt(
            question=request.question,
            chunks=context_result.chunks,
        )
        if low_confidence:
            prompt = f"{prompt}\n\n{LOW_CONFIDENCE_INSTRUCTION}"

        llm_response = await self.llm_client.generate(
            prompt=prompt,
            system_prompt=RAG_SYSTEM_PROMPT,
        )

        return ChatResponse(
            answer=llm_response.content,
            citations=[
                self._to_chat_citation(citation)
                for citation in context_result.citations
            ],
            low_confidence=low_confidence,
            used_context=True,
        )

    def _filter_quality(
        self,
        results: list[QdrantSearchResult],
    ) -> list[QdrantSearchResult]:
        qualified_results = [
            result
            for result in results
            if result.score >= settings.retrieval_score_threshold
        ]

        if len(qualified_results) <= 1:
            return qualified_results

        top_score = qualified_results[0].score
        last_score = qualified_results[-1].score
        if top_score - last_score <= SCORE_SPREAD_THRESHOLD:
            return qualified_results

        return [
            result
            for result in qualified_results
            if result.score >= top_score - TOP_SCORE_WINDOW
        ]

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
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    vector_store: QdrantVectorStore = Depends(get_vector_store),
    reranker_service: RerankerService = Depends(get_reranker_service),
) -> ChatService:
    return ChatService(
        hybrid_retriever=HybridRetriever(
            embedding_service=embedding_service,
            vector_store=vector_store,
        ),
        reranker_service=reranker_service,
        context_builder=ContextBuilder(),
        llm_client=get_gemini_client(),
    )
