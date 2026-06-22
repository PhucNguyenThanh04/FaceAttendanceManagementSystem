# Handoff Summary — RAG Chatbox

## 1. Project goal

`rag-chatbox` là FastAPI microservice cho chatbot RAG nội bộ của hệ thống HR/chấm công. Mục tiêu: nhận tài liệu chính sách/nội quy tiếng Việt, index vào Qdrant bằng BGE-M3 dense+sparse embeddings, rồi trả lời câu hỏi nhân viên/HR bằng Gemini với citation theo tài liệu nội bộ.

## 2. Current architecture

Runtime chính:

```text
run.py -> src.main:app
FastAPI lifespan
  -> Redis ping
  -> load/warmup EmbeddingClient(BGE-M3)
  -> ensure Qdrant collection
  -> load/warmup RerankerClient
  -> build IngestionPipeline
  -> store services in app.state
```

API:

- `GET /health`
- `POST /api/v1/rag/documents`: upload/index document
- `POST /api/v1/chat`: retrieve/rerank/context/Gemini answer

Ingestion flow:

```text
UploadFile + metadata
  -> LoaderFactory(.pdf/.docx/.txt)
  -> LegalStructureAwareChunker
  -> DocumentIndexer
  -> EmbeddingService(BGE-M3 dense+sparse)
  -> QdrantVectorStore.upsert_points
```

Chat flow:

```text
question + user_role
  -> HybridRetriever
  -> Qdrant RRF dense+sparse search with allowed_role filter
  -> RerankerService
  -> ChatService quality filter
  -> ContextBuilder
  -> PromptBuilder.build_rag_prompt
  -> GeminiClient.generate
  -> ChatResponse(answer, citations, low_confidence, used_context)
```

Implemented core modules: `core`, `api/v1`, `features/chat`, `features/documents`, `rag/ingestion`, `rag/embeddings`, `rag/retrieval`, `integrations/llm`, `integrations/qdrant`, `integrations/cache`.

Empty/planned modules: `agents`, `routing`, `tools`, `guardrails`, `observability`, `integrations/web_search/client.py`, `core/exceptions.py`.

## 3. Files changed

No source changes made in the last scan turn.

Current handoff file updated:

- `handoff_summary.md`

Repo also has unrelated dirty files outside this service under `../api-service/`, plus local changes in `src/core/settings.py`, `src/core/dependenci.py`, `src/main.py`, and new `src/integrations/cache/` from prior work.

## 4. Public interfaces đã chốt

HTTP:

- `POST /api/v1/rag/documents`
  - multipart form: `document_id`, `filename`, `file_path`, `allowed_roles`, `file`
  - returns `DocumentIngestResponse`
- `POST /api/v1/chat`
  - body: `ChatRequest(question: str, user_role: str)`
  - returns `ChatResponse(answer, citations, low_confidence, used_context)`
- Auth: `X-API-Key`, checked by `verify_api_key`.

Internal:

- `IngestionPipeline.ingestion(...) -> IngestionResult`
- `LoaderFactory.load(file, allowed_roles, extra_metadata) -> list[Document]`
- `LegalStructureAwareChunker.chunk(documents) -> list[DocumentChunk]`
- `DocumentIndexer.index_chunks(...) -> int`
- `EmbeddingService.embed_query_hybrid(query) -> EmbeddingBatch`
- `QdrantVectorStore.search_hybrid(...) -> list[QdrantSearchResult]`
- `RerankerService.rerank(query, results, top_n=None) -> list[QdrantSearchResult]`
- `ContextBuilder.build(results, max_tokens=3000) -> ContextBuildResult`
- `GeminiClient.generate(prompt, system_prompt=...) -> LLMResponse`

## 5. Decisions made

- Direct RAG pipeline is active; agent/planner/tool routing is scaffolded but unused.
- Use BGE-M3 for both dense vectors and sparse lexical vectors.
- Qdrant collection uses named vectors from settings: dense + sparse.
- Hybrid retrieval uses Qdrant server-side RRF fusion via `FusionQuery`.
- Permission filtering currently happens in Qdrant query using `allowed_role`.
- Reranker and embedding model inference are sync model calls wrapped by async services with single-worker `ThreadPoolExecutor`.
- Chunking is Vietnamese legal/policy aware: section -> clause/khoản -> point/điểm -> recursive fallback.
- Chunk IDs are deterministic UUID v5 from source/section/content prefix for idempotent upsert.
- Prompts are Vietnamese and instruct Gemini to answer only from supplied context, with citations.

## 6. Known bugs/TODO

- `src/integrations/cache/redis_client.py` references `settings.redis_db_session` and `settings.redis_session_url`, but `Settings` only defines `redis_host`, `redis_port`, `redis_password`, `redis_url`.
- `QdrantClientManager.ensure_default_collections()` references `settings.qdrant_collection_law`, not defined in `Settings`.
- `redis_client.py` imports `redis.asyncio`, but `requirements.txt` does not visibly include `redis`.
- `ChatService` catches all unexpected router errors as HTTP 500 with raw exception text.
- `ChatCitation` / `ChatResponse` use mutable default lists; prefer `Field(default_factory=list)`.
- Existing `project_structure_analysis.md` is stale: it says chat/retrieval are empty, but current source implements them.
- No test suite currently present for ingestion, retrieval, reranking, context budgeting, or API behavior.
- Many planned agentic modules are still zero-byte placeholders.

## 7. Next task

Fix startup/config blockers first:

1. Align Redis settings and `create_redis_async_client()`.
2. Remove or define `qdrant_collection_law`.
3. Confirm `redis` dependency in `requirements.txt`.
4. Then run a minimal startup/import check and add focused tests for `ChatService`, `ContextBuilder`, and `LegalStructureAwareChunker`.
